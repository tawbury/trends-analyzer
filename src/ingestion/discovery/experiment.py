from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ingestion.discovery.rules import DiscoveryRuleConfig


@dataclass(frozen=True)
class DiscoveryExperimentMetadata:
    generated_at: str
    provider: str
    rule_config_path: str
    rule_config_fingerprint: str
    active_source_symbol_policy: str
    selected_symbol_count: int
    query_count: int = 0


def build_experiment_metadata(
    *,
    generated_at: datetime,
    provider: str,
    rules: DiscoveryRuleConfig,
    rule_config_path: str = "",
    active_source_symbol_policy: str = "unknown",
    selected_symbol_count: int = 0,
    query_count: int = 0,
) -> DiscoveryExperimentMetadata:
    return DiscoveryExperimentMetadata(
        generated_at=generated_at.isoformat(),
        provider=provider,
        rule_config_path=_display_path(rule_config_path),
        rule_config_fingerprint=fingerprint_rule_config(rules),
        active_source_symbol_policy=active_source_symbol_policy,
        selected_symbol_count=selected_symbol_count,
        query_count=query_count,
    )


def fingerprint_rule_config(rules: DiscoveryRuleConfig) -> str:
    payload = rule_config_to_dict(rules)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def rule_config_to_dict(rules: DiscoveryRuleConfig) -> dict[str, Any]:
    return _jsonable(asdict(rules))


def _jsonable(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in sorted(value.items())}
    return value


def _display_path(path: str) -> str:
    if not path:
        return "default"
    return str(Path(path).expanduser())
