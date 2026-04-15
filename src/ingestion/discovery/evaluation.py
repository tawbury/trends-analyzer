from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord


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
_GENERIC_NOISE_TERMS = {
    "증시",
    "코스피",
    "코스닥",
    "특징주",
    "관련주",
    "상승",
    "하락",
    "급등",
    "급락",
    "마감",
}


def evaluate_discovery_item(
    *,
    item: RawNewsItem,
    record: SymbolRecord,
    query: str,
    as_of: datetime,
) -> DiscoveryEvaluation:
    text = f"{item.title} {item.body}".lower()
    reasons: list[str] = []
    score = 0.0
    suspicious = False

    if item.title.strip():
        score += 0.2
        reasons.append("title_present")
    else:
        reasons.append("missing_title")

    if item.body.strip():
        score += 0.15
        reasons.append("body_present")
    else:
        reasons.append("missing_body")

    match_strength = _match_strength(
        text=text,
        record=record,
        query=query,
    )
    score += match_strength
    if match_strength >= 0.45:
        reasons.append("strong_symbol_or_query_match")
    elif match_strength >= 0.2:
        reasons.append("weak_symbol_or_query_match")
    else:
        reasons.append("missing_symbol_or_query_match")
        suspicious = True

    if item.url.strip():
        score += 0.1
        reasons.append("url_present")
    else:
        reasons.append("missing_url")
        suspicious = True

    if item.metadata.get("provider_payload"):
        score += 0.05
        reasons.append("provider_payload_present")
    else:
        reasons.append("missing_provider_payload")

    if _is_publish_time_plausible(item.published_at, as_of):
        score += 0.1
        reasons.append("publish_time_plausible")
    else:
        reasons.append("publish_time_suspicious")
        suspicious = True

    if _is_generic_noise(item=item, record=record, query=query):
        score -= 0.25
        reasons.append("generic_noise_pattern")
        suspicious = True

    score = max(0.0, min(score, 1.0))
    if score >= 0.65 and not suspicious:
        decision = DiscoveryDecision.KEEP
    elif score >= 0.4:
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
        return 0.45

    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    matched = sum(1 for token in query_tokens if token in text)
    return 0.3 * (matched / len(query_tokens))


def _is_publish_time_plausible(published_at: datetime, as_of: datetime) -> bool:
    return as_of - timedelta(days=30) <= published_at <= as_of + timedelta(minutes=10)


def _is_generic_noise(
    *,
    item: RawNewsItem,
    record: SymbolRecord,
    query: str,
) -> bool:
    title_tokens = set(_tokens(item.title))
    text = f"{item.title} {item.body}".lower()
    has_generic_title = bool(title_tokens & _GENERIC_NOISE_TERMS)
    names = _unique_non_empty([record.korean_name, record.name, record.normalized_name, query])
    has_name_match = any(name.lower() in text for name in names)
    return has_generic_title and not has_name_match


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
