from __future__ import annotations

from collections import defaultdict
from typing import Any


DecisionCount = dict[str, int]


def build_calibration_comparison(
    *,
    provider: str,
    generated_at: str,
    current_payload: dict[str, Any],
    previous_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if previous_payload is None:
        return {
            "provider": provider,
            "generated_at": generated_at,
            "available": False,
            "reason": "previous_review_not_found",
            "current_run": _run_metadata(current_payload),
            "previous_run": None,
        }

    previous_items = _items(previous_payload)
    current_items = _items(current_payload)
    previous_noisy_queries = _noisy_query_sample(previous_payload, previous_items)
    current_noisy_queries = _noisy_query_sample(current_payload, current_items)

    return {
        "provider": provider,
        "generated_at": generated_at,
        "available": True,
        "current_run": _run_metadata(current_payload),
        "previous_run": _run_metadata(previous_payload),
        "decision_counts": _compare_counts(
            _decision_counts(previous_items),
            _decision_counts(current_items),
        ),
        "suspicious_count": _compare_scalar(
            _suspicious_count(previous_items),
            _suspicious_count(current_items),
        ),
        "per_origin_counts": _compare_grouped_counts(
            _grouped_decision_counts(previous_items, "query_origin"),
            _grouped_decision_counts(current_items, "query_origin"),
        ),
        "per_classification_counts": _compare_grouped_counts(
            _grouped_decision_counts(previous_items, "classification"),
            _grouped_decision_counts(current_items, "classification"),
        ),
        "noisy_query_sample_changes": {
            "previous": previous_noisy_queries,
            "current": current_noisy_queries,
            "added": _sample_added(previous_noisy_queries, current_noisy_queries),
            "removed": _sample_removed(previous_noisy_queries, current_noisy_queries),
        },
    }


def _run_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("experiment_metadata")
    if isinstance(metadata, dict):
        return metadata
    return {
        "generated_at": payload.get("generated_at", ""),
        "provider": payload.get("provider", ""),
        "rule_config_path": "unknown",
        "rule_config_fingerprint": "unknown",
        "active_source_symbol_policy": "unknown",
        "selected_symbol_count": 0,
        "query_count": 0,
    }


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _decision_counts(items: list[dict[str, Any]]) -> DecisionCount:
    counts = _empty_counts()
    for item in items:
        decision = str(item.get("discovery_decision") or "drop")
        counts[decision if decision in counts else "drop"] += 1
    return counts


def _suspicious_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if bool(item.get("discovery_suspicious")))


def _grouped_decision_counts(
    items: list[dict[str, Any]],
    group_key: str,
) -> dict[str, DecisionCount]:
    grouped: dict[str, DecisionCount] = defaultdict(_empty_counts)
    for item in items:
        group_value = str(item.get(group_key) or "unknown")
        decision = str(item.get("discovery_decision") or "drop")
        grouped[group_value][decision if decision in grouped[group_value] else "drop"] += 1
    return dict(sorted(grouped.items()))


def _compare_counts(previous: DecisionCount, current: DecisionCount) -> dict[str, DecisionCount]:
    return {
        "previous": previous,
        "current": current,
        "delta": _delta_counts(previous, current),
    }


def _compare_scalar(previous: int, current: int) -> dict[str, int]:
    return {
        "previous": previous,
        "current": current,
        "delta": current - previous,
    }


def _compare_grouped_counts(
    previous: dict[str, DecisionCount],
    current: dict[str, DecisionCount],
) -> dict[str, dict[str, DecisionCount]]:
    keys = sorted(set(previous) | set(current))
    return {
        key: _compare_counts(
            previous.get(key, _empty_counts()),
            current.get(key, _empty_counts()),
        )
        for key in keys
    }


def _delta_counts(previous: DecisionCount, current: DecisionCount) -> DecisionCount:
    return {
        decision: current.get(decision, 0) - previous.get(decision, 0)
        for decision in ("keep", "weak_keep", "drop")
    }


def _empty_counts() -> DecisionCount:
    return {"keep": 0, "weak_keep": 0, "drop": 0}


def _noisy_query_sample(
    payload: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[str]:
    summary = payload.get("calibration_summary")
    if isinstance(summary, dict):
        sample = summary.get("noisy_query_sample")
        if isinstance(sample, list):
            return [str(item) for item in sample[:5]]

    result: list[str] = []
    for item in items:
        if item.get("discovery_decision") == "drop":
            query = str(item.get("query") or "")
            if query and query not in result:
                result.append(query)
            if len(result) >= 5:
                break
    return result


def _sample_added(previous: list[str], current: list[str]) -> list[str]:
    previous_set = set(previous)
    return [item for item in current if item not in previous_set]


def _sample_removed(previous: list[str], current: list[str]) -> list[str]:
    current_set = set(current)
    return [item for item in previous if item not in current_set]
