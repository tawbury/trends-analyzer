from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord
from src.ingestion.discovery.rules import DiscoveryRuleConfig


class DiscoveryDecision(StrEnum):
    KEEP = "keep"
    WEAK_KEEP = "weak_keep"
    DROP = "drop"


@dataclass(frozen=True)
class DiscoveryEvaluation:
    decision: DiscoveryDecision
    score: float
    reasons: list[str] = field(default_factory=list)
    suspicious: bool = False


_TOKEN_RE = re.compile(r"[^\w가-힣]+")


def evaluate_discovery_item(
    *,
    item: RawNewsItem,
    record: SymbolRecord,
    query: str,
    query_origin: str = "",
    as_of: datetime,
    rules: DiscoveryRuleConfig | None = None,
) -> DiscoveryEvaluation:
    resolved_rules = rules or DiscoveryRuleConfig()
    text = f"{item.title} {item.body}".lower()
    reasons: list[str] = []
    score = 0.0
    suspicious = False
    classification = _classification(record)
    origin_rule = resolved_rules.origin_rule_for(query_origin)

    if item.title.strip():
        score += resolved_rules.title_present_score
        reasons.append("title_present")
    else:
        reasons.append("missing_title")

    if item.body.strip():
        score += resolved_rules.body_present_score
        reasons.append("body_present")
    else:
        reasons.append("missing_body")

    match_strength = _match_strength(
        text=text,
        record=record,
        query=query,
        rules=resolved_rules,
    )
    score += match_strength
    if match_strength >= resolved_rules.strong_match_threshold:
        reasons.append("strong_symbol_or_query_match")
    elif match_strength >= resolved_rules.weak_match_threshold:
        reasons.append("weak_symbol_or_query_match")
    else:
        reasons.append("missing_symbol_or_query_match")
        suspicious = True

    if item.url.strip():
        score += resolved_rules.url_present_score
        reasons.append("url_present")
    else:
        reasons.append("missing_url")
        suspicious = True

    if item.metadata.get("provider_payload"):
        score += resolved_rules.provider_payload_score
        reasons.append("provider_payload_present")
    else:
        reasons.append("missing_provider_payload")

    if _is_publish_time_plausible(item.published_at, as_of, rules=resolved_rules):
        score += resolved_rules.publish_time_score
        reasons.append("publish_time_plausible")
    else:
        reasons.append("publish_time_suspicious")
        suspicious = True

    if _is_origin_query_too_weak(query=query, origin_rule=origin_rule):
        score += origin_rule.score_adjustment
        reasons.append(f"origin_{query_origin or 'unknown'}_query_too_weak")
        suspicious = True
    elif origin_rule.score_adjustment:
        score += origin_rule.score_adjustment
        reasons.append(f"origin_{query_origin}_score_adjustment")

    classification_adjustment = resolved_rules.classification_score_adjustment(classification)
    if classification_adjustment:
        score += classification_adjustment
        reasons.append(f"classification_{classification}_score_adjustment")

    if _is_generic_noise(item=item, record=record, query=query, rules=resolved_rules):
        score += resolved_rules.generic_noise_penalty
        reasons.append("generic_noise_pattern")
        suspicious = True

    score = max(0.0, min(score, 1.0))
    keep_threshold, weak_keep_threshold = resolved_rules.thresholds_for(classification)
    if score >= keep_threshold and not suspicious:
        decision = DiscoveryDecision.KEEP
    elif score >= weak_keep_threshold:
        decision = DiscoveryDecision.WEAK_KEEP
    else:
        decision = DiscoveryDecision.DROP

    return DiscoveryEvaluation(
        decision=decision,
        score=round(score, 3),
        reasons=reasons,
        suspicious=suspicious,
    )


def attach_discovery_metadata(
    *,
    item: RawNewsItem,
    evaluation: DiscoveryEvaluation,
) -> RawNewsItem:
    return replace(
        item,
        metadata={
            **item.metadata,
            "discovery_decision": evaluation.decision.value,
            "discovery_score": f"{evaluation.score:.3f}",
            "discovery_reasons": ",".join(evaluation.reasons),
            "discovery_suspicious": str(evaluation.suspicious).lower(),
        },
    )


def _match_strength(
    *,
    text: str,
    record: SymbolRecord,
    query: str,
    rules: DiscoveryRuleConfig,
) -> float:
    names = _unique_non_empty(
        [
            record.korean_name,
            record.name,
            record.normalized_name,
            *record.aliases,
            query,
        ]
    )
    if any(name.lower() in text for name in names):
        return rules.exact_match_score

    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    matched = sum(1 for token in query_tokens if token in text)
    return rules.token_overlap_score * (matched / len(query_tokens))


def _is_publish_time_plausible(
    published_at: datetime,
    as_of: datetime,
    *,
    rules: DiscoveryRuleConfig,
) -> bool:
    return (
        as_of - timedelta(days=rules.publish_past_window_days)
        <= published_at
        <= as_of + timedelta(minutes=rules.publish_future_window_minutes)
    )


def _is_generic_noise(
    *,
    item: RawNewsItem,
    record: SymbolRecord,
    query: str,
    rules: DiscoveryRuleConfig,
) -> bool:
    title_tokens = set(_tokens(item.title))
    text = f"{item.title} {item.body}".lower()
    has_generic_title = bool(title_tokens & rules.generic_noise_terms)
    names = _unique_non_empty([record.korean_name, record.name, record.normalized_name, query])
    has_name_match = any(name.lower() in text for name in names)
    return has_generic_title and not has_name_match


def _is_origin_query_too_weak(*, query: str, origin_rule) -> bool:
    if origin_rule.min_query_length and len(query.strip()) < origin_rule.min_query_length:
        return True
    if origin_rule.min_token_count and len(_tokens(query)) < origin_rule.min_token_count:
        return True
    return False


def _classification(record: SymbolRecord) -> str:
    return record.metadata.get("classification") or record.security_type or "unknown"


def _tokens(value: str) -> list[str]:
    return [token for token in _TOKEN_RE.sub(" ", value.lower()).split() if token]


def _unique_non_empty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
