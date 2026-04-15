from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OriginRule:
    score_adjustment: float = 0.0
    min_query_length: int = 0
    min_token_count: int = 0


@dataclass(frozen=True)
class ClassificationRule:
    keep_threshold: float | None = None
    weak_keep_threshold: float | None = None
    score_adjustment: float = 0.0


@dataclass(frozen=True)
class DiscoveryRuleConfig:
    generic_noise_terms: set[str] = field(
        default_factory=lambda: {
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
    )
    keep_threshold: float = 0.65
    weak_keep_threshold: float = 0.4
    strong_match_threshold: float = 0.45
    weak_match_threshold: float = 0.2
    publish_past_window_days: int = 30
    publish_future_window_minutes: int = 10
    title_present_score: float = 0.2
    body_present_score: float = 0.15
    url_present_score: float = 0.1
    provider_payload_score: float = 0.05
    publish_time_score: float = 0.1
    exact_match_score: float = 0.45
    token_overlap_score: float = 0.3
    generic_noise_penalty: float = -0.25
    origin_rules: dict[str, OriginRule] = field(
        default_factory=lambda: {
            "korean_name": OriginRule(),
            "name": OriginRule(),
            "normalized_name": OriginRule(),
            "alias": OriginRule(score_adjustment=0.0, min_query_length=2),
            "query_keyword": OriginRule(score_adjustment=0.0, min_token_count=1),
        }
    )
    classification_rules: dict[str, ClassificationRule] = field(default_factory=dict)

    def thresholds_for(self, classification: str) -> tuple[float, float]:
        rule = self.classification_rules.get(classification)
        if rule is None:
            return self.keep_threshold, self.weak_keep_threshold
        return (
            rule.keep_threshold if rule.keep_threshold is not None else self.keep_threshold,
            rule.weak_keep_threshold
            if rule.weak_keep_threshold is not None
            else self.weak_keep_threshold,
        )

    def origin_rule_for(self, origin: str) -> OriginRule:
        return self.origin_rules.get(origin, OriginRule())

    def classification_score_adjustment(self, classification: str) -> float:
        rule = self.classification_rules.get(classification)
        return rule.score_adjustment if rule else 0.0


def load_discovery_rule_config(path: str) -> DiscoveryRuleConfig:
    if not path:
        return DiscoveryRuleConfig()
    config_path = Path(path).expanduser()
    if not config_path.exists():
        return DiscoveryRuleConfig()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return DiscoveryRuleConfig()
    return discovery_rule_config_from_dict(payload)


def discovery_rule_config_from_dict(payload: dict[str, Any]) -> DiscoveryRuleConfig:
    config = DiscoveryRuleConfig()
    if "generic_noise_terms" in payload:
        config = replace(
            config,
            generic_noise_terms={str(item) for item in payload["generic_noise_terms"]},
        )
    scalar_fields = {
        "keep_threshold": float,
        "weak_keep_threshold": float,
        "strong_match_threshold": float,
        "weak_match_threshold": float,
        "publish_past_window_days": int,
        "publish_future_window_minutes": int,
        "title_present_score": float,
        "body_present_score": float,
        "url_present_score": float,
        "provider_payload_score": float,
        "publish_time_score": float,
        "exact_match_score": float,
        "token_overlap_score": float,
        "generic_noise_penalty": float,
    }
    updates: dict[str, Any] = {}
    for field_name, caster in scalar_fields.items():
        if field_name in payload:
            updates[field_name] = caster(payload[field_name])
    if updates:
        config = replace(config, **updates)
    if isinstance(payload.get("origin_rules"), dict):
        config = replace(
            config,
            origin_rules=_origin_rules_from_dict(
                base=config.origin_rules,
                payload=payload["origin_rules"],
            ),
        )
    if isinstance(payload.get("classification_rules"), dict):
        config = replace(
            config,
            classification_rules=_classification_rules_from_dict(
                payload["classification_rules"]
            ),
        )
    return config


def _origin_rules_from_dict(
    *,
    base: dict[str, OriginRule],
    payload: dict[str, Any],
) -> dict[str, OriginRule]:
    rules = dict(base)
    for origin, value in payload.items():
        if not isinstance(value, dict):
            continue
        current = rules.get(origin, OriginRule())
        rules[str(origin)] = replace(
            current,
            score_adjustment=float(value.get("score_adjustment", current.score_adjustment)),
            min_query_length=int(value.get("min_query_length", current.min_query_length)),
            min_token_count=int(value.get("min_token_count", current.min_token_count)),
        )
    return rules


def _classification_rules_from_dict(payload: dict[str, Any]) -> dict[str, ClassificationRule]:
    rules: dict[str, ClassificationRule] = {}
    for classification, value in payload.items():
        if not isinstance(value, dict):
            continue
        rules[str(classification)] = ClassificationRule(
            keep_threshold=_optional_float(value.get("keep_threshold")),
            weak_keep_threshold=_optional_float(value.get("weak_keep_threshold")),
            score_adjustment=float(value.get("score_adjustment", 0.0)),
        )
    return rules


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
