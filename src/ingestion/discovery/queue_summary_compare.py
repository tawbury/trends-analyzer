from __future__ import annotations

from datetime import datetime
from typing import Any


def compare_queue_summaries(
    *,
    current_summary: dict[str, Any],
    previous_summary: dict[str, Any] | None,
    current_summary_path: str = "",
    previous_summary_path: str = "",
) -> dict[str, Any]:
    base = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "comparison_available": previous_summary is not None,
        "current_summary_path": current_summary_path,
        "previous_summary_path": previous_summary_path,
    }
    if previous_summary is None:
        return {
            **base,
            "unavailable_reason": "previous_summary_not_found",
            "current_selected_count": int(current_summary.get("selected_count") or 0),
        }

    return {
        **base,
        "unavailable_reason": "",
        "provider": {
            "current": str(current_summary.get("provider") or ""),
            "previous": str(previous_summary.get("provider") or ""),
        },
        "generated_at_values": {
            "current": str(current_summary.get("generated_at") or ""),
            "previous": str(previous_summary.get("generated_at") or ""),
        },
        "count_deltas": {
            "selected_count": _numeric_delta(current_summary, previous_summary, "selected_count"),
            "reviewed_count": _numeric_delta(current_summary, previous_summary, "reviewed_count"),
            "unreviewed_count": _numeric_delta(current_summary, previous_summary, "unreviewed_count"),
        },
        "matched_signal_count_deltas": _count_map_delta(
            current_summary.get("matched_signal_counts"),
            previous_summary.get("matched_signal_counts"),
        ),
        "rereview_reason_count_deltas": _count_map_delta(
            current_summary.get("rereview_reason_counts"),
            previous_summary.get("rereview_reason_counts"),
        ),
        "priority_score_bucket_deltas": _count_map_delta(
            current_summary.get("priority_score_buckets"),
            previous_summary.get("priority_score_buckets"),
        ),
        "top_matched_signal_comparison": _top_matched_signal_comparison(
            current_summary.get("top_matched_signals"),
            previous_summary.get("top_matched_signals"),
        ),
        "metadata_comparison": _metadata_comparison(
            current_summary=current_summary,
            previous_summary=previous_summary,
        ),
    }


def _numeric_delta(
    current_summary: dict[str, Any],
    previous_summary: dict[str, Any],
    key: str,
) -> dict[str, int]:
    current = int(current_summary.get(key) or 0)
    previous = int(previous_summary.get(key) or 0)
    return {
        "current": current,
        "previous": previous,
        "delta": current - previous,
    }


def _count_map_delta(current_value: Any, previous_value: Any) -> dict[str, dict[str, int]]:
    current = _as_int_map(current_value)
    previous = _as_int_map(previous_value)
    result: dict[str, dict[str, int]] = {}
    for key in sorted(set(current) | set(previous)):
        current_count = current.get(key, 0)
        previous_count = previous.get(key, 0)
        result[key] = {
            "current": current_count,
            "previous": previous_count,
            "delta": current_count - previous_count,
        }
    return result


def _as_int_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        result[str(key)] = int(count or 0)
    return result


def _top_matched_signal_comparison(current_value: Any, previous_value: Any) -> dict[str, Any]:
    current = _top_signal_values(current_value)
    previous = _top_signal_values(previous_value)
    return {
        "current": current,
        "previous": previous,
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "unchanged": sorted(set(current) & set(previous)),
    }


def _top_signal_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict) and item.get("value"):
            result.append(str(item["value"]))
    return result


def _metadata_comparison(
    *,
    current_summary: dict[str, Any],
    previous_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "applied_disagreement_presets": _list_comparison(
            current_summary.get("applied_disagreement_presets"),
            previous_summary.get("applied_disagreement_presets"),
        ),
        "applied_assist_presets": _list_comparison(
            current_summary.get("applied_assist_presets"),
            previous_summary.get("applied_assist_presets"),
        ),
        "applied_queue_signals": _list_comparison(
            current_summary.get("applied_queue_signals"),
            previous_summary.get("applied_queue_signals"),
        ),
        "filter_differences": _filter_differences(
            current_summary.get("applied_filters"),
            previous_summary.get("applied_filters"),
        ),
        "output": {
            "current_path": str(current_summary.get("output_path") or ""),
            "previous_path": str(previous_summary.get("output_path") or ""),
            "current_format": str(current_summary.get("output_format") or ""),
            "previous_format": str(previous_summary.get("output_format") or ""),
        },
    }


def _list_comparison(current_value: Any, previous_value: Any) -> dict[str, Any]:
    current = _as_string_list(current_value)
    previous = _as_string_list(previous_value)
    return {
        "current": current,
        "previous": previous,
        "added": [value for value in current if value not in previous],
        "removed": [value for value in previous if value not in current],
        "changed": current != previous,
    }


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _filter_differences(current_value: Any, previous_value: Any) -> dict[str, dict[str, Any]]:
    current = current_value if isinstance(current_value, dict) else {}
    previous = previous_value if isinstance(previous_value, dict) else {}
    result: dict[str, dict[str, Any]] = {}
    for key in sorted(set(current) | set(previous)):
        current_item = current.get(key)
        previous_item = previous.get(key)
        if current_item != previous_item:
            result[str(key)] = {
                "current": current_item,
                "previous": previous_item,
            }
    return result
