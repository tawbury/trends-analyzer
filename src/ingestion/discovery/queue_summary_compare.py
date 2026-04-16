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

    comparison = {
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
    comparison["interpretation_hints"] = _interpretation_hints(comparison)
    comparison["strategy_notes"] = _strategy_notes(comparison)
    return comparison


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


def _interpretation_hints(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    count_deltas = comparison.get("count_deltas")
    priority_deltas = comparison.get("priority_score_bucket_deltas")
    signal_deltas = comparison.get("matched_signal_count_deltas")
    metadata = comparison.get("metadata_comparison")
    if not isinstance(count_deltas, dict):
        return hints
    if not isinstance(priority_deltas, dict):
        priority_deltas = {}
    if not isinstance(signal_deltas, dict):
        signal_deltas = {}
    if not isinstance(metadata, dict):
        metadata = {}

    selected_delta = _delta_value(count_deltas, "selected_count")
    high_priority_delta = _delta_value(priority_deltas, "100_plus")
    if selected_delta < 0 and high_priority_delta > 0:
        hints.append(
            _hint(
                hint_type="more_concentrated_high_priority_queue",
                message=(
                    "selected_count decreased while the 100_plus priority bucket increased; "
                    "the queue may be more concentrated on high-value review candidates."
                ),
                evidence={
                    "selected_count_delta": selected_delta,
                    "priority_100_plus_delta": high_priority_delta,
                },
            )
        )
    elif selected_delta > 0 and high_priority_delta <= 0:
        hints.append(
            _hint(
                hint_type="larger_queue_without_high_priority_gain",
                message=(
                    "selected_count increased without a 100_plus priority bucket increase; "
                    "review workload may have expanded without a clear top-priority gain."
                ),
                evidence={
                    "selected_count_delta": selected_delta,
                    "priority_100_plus_delta": high_priority_delta,
                },
            )
        )

    false_keep_delta = _delta_value(signal_deltas, "false_keep_focus")
    if false_keep_delta > 0:
        hints.append(
            _hint(
                hint_type="false_keep_focus_increased",
                message=(
                    "false_keep_focus matches increased; this queue emphasizes items that "
                    "automatic rules kept but humans previously marked as drop."
                ),
                evidence={"false_keep_focus_delta": false_keep_delta},
            )
        )

    false_drop_delta = _delta_value(signal_deltas, "false_drop_focus")
    if false_drop_delta > 0:
        hints.append(
            _hint(
                hint_type="false_drop_focus_increased",
                message=(
                    "false_drop_focus matches increased; this queue emphasizes items that "
                    "automatic rules dropped but humans previously wanted to keep."
                ),
                evidence={"false_drop_focus_delta": false_drop_delta},
            )
        )

    noisy_delta = _delta_value(signal_deltas, "noisy_query_focus")
    suspicious_delta = _delta_value(signal_deltas, "suspicious_focus")
    if noisy_delta > 0 or suspicious_delta > 0:
        hints.append(
            _hint(
                hint_type="noise_or_suspicious_focus_increased",
                message=(
                    "suspicious/noisy signal share increased; this strategy may be better "
                    "for cleaning noisy discovery candidates but could require more rejection review."
                ),
                evidence={
                    "noisy_query_focus_delta": noisy_delta,
                    "suspicious_focus_delta": suspicious_delta,
                },
            )
        )

    repeated_query_delta = _delta_value(signal_deltas, "repeated_query_disagreement")
    assist_repeated_query_delta = _delta_value(signal_deltas, "assist_repeated_query_disagreement")
    if repeated_query_delta > 0 or assist_repeated_query_delta > 0:
        hints.append(
            _hint(
                hint_type="repeated_query_disagreement_emphasis_increased",
                message=(
                    "repeated query disagreement emphasis increased; inspect recurring noisy "
                    "queries or query-specific rule penalties."
                ),
                evidence={
                    "repeated_query_disagreement_delta": repeated_query_delta,
                    "assist_repeated_query_disagreement_delta": assist_repeated_query_delta,
                },
            )
        )

    reviewed_delta = _delta_value(count_deltas, "reviewed_count")
    unreviewed_delta = _delta_value(count_deltas, "unreviewed_count")
    if reviewed_delta > 0 and reviewed_delta >= max(unreviewed_delta, 0):
        hints.append(
            _hint(
                hint_type="queue_became_more_reviewed_heavy",
                message=(
                    "reviewed_count increased more than unreviewed_count; this strategy may "
                    "be better suited for targeted re-review than first-pass labeling."
                ),
                evidence={
                    "reviewed_count_delta": reviewed_delta,
                    "unreviewed_count_delta": unreviewed_delta,
                },
            )
        )
    elif unreviewed_delta > 0 and unreviewed_delta > max(reviewed_delta, 0):
        hints.append(
            _hint(
                hint_type="queue_became_more_unreviewed_heavy",
                message=(
                    "unreviewed_count increased more than reviewed_count; this strategy may "
                    "expand first-pass review coverage."
                ),
                evidence={
                    "reviewed_count_delta": reviewed_delta,
                    "unreviewed_count_delta": unreviewed_delta,
                },
            )
        )

    filter_differences = metadata.get("filter_differences")
    if isinstance(filter_differences, dict) and filter_differences:
        hints.append(
            _hint(
                hint_type="filters_changed",
                message=(
                    "queue filters changed between summaries; interpret composition changes "
                    "together with filter differences, not as signal quality changes alone."
                ),
                evidence={"changed_filters": sorted(filter_differences)},
            )
        )

    return hints


def _strategy_notes(comparison: dict[str, Any]) -> list[str]:
    hints = comparison.get("interpretation_hints")
    if not isinstance(hints, list) or not hints:
        return [
            "No strong interpretation hints were triggered; inspect raw deltas before changing strategy."
        ]
    notes: list[str] = []
    hint_types = {
        str(hint.get("type") or "")
        for hint in hints
        if isinstance(hint, dict)
    }
    if "more_concentrated_high_priority_queue" in hint_types:
        notes.append(
            "Consider using this strategy for smaller high-value review sessions."
        )
    if "larger_queue_without_high_priority_gain" in hint_types:
        notes.append(
            "Consider tightening presets or max_items if operator capacity is limited."
        )
    if "noise_or_suspicious_focus_increased" in hint_types:
        notes.append(
            "Review noisy/suspicious rows separately from relevance recovery rows."
        )
    if "repeated_query_disagreement_emphasis_increased" in hint_types:
        notes.append(
            "Inspect repeated query terms before changing broad origin or classification thresholds."
        )
    if "queue_became_more_reviewed_heavy" in hint_types:
        notes.append(
            "Use this queue for re-review calibration rather than measuring new coverage."
        )
    if "queue_became_more_unreviewed_heavy" in hint_types:
        notes.append(
            "Use this queue when the goal is broader first-pass labeling coverage."
        )
    return notes


def _delta_value(values: dict[str, Any], key: str) -> int:
    payload = values.get(key)
    if not isinstance(payload, dict):
        return 0
    return int(payload.get("delta") or 0)


def _hint(*, hint_type: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": hint_type,
        "message": message,
        "evidence": evidence,
    }
