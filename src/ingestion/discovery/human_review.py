from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from src.ingestion.discovery.review import build_review_item_id

DISCOVERY_LABELS = {"keep", "weak_keep", "drop"}


@dataclass(frozen=True)
class HumanReviewFeedback:
    item_ref: str
    human_label: str
    note: str = ""
    rule_feedback_tag: str = ""
    reviewed_at: str = ""


def human_review_feedback_from_dict(payload: dict[str, Any]) -> HumanReviewFeedback:
    item_ref = str(payload.get("item_ref") or payload.get("review_item_id") or "").strip()
    human_label = str(payload.get("human_label") or "").strip()
    if not item_ref:
        raise ValueError("Human review feedback requires item_ref")
    if human_label not in DISCOVERY_LABELS:
        raise ValueError(f"Unsupported human_label: {human_label}")
    reviewed_at = str(payload.get("reviewed_at") or "").strip()
    if not reviewed_at:
        reviewed_at = datetime.now().astimezone().isoformat()
    return HumanReviewFeedback(
        item_ref=item_ref,
        human_label=human_label,
        note=str(payload.get("note") or ""),
        rule_feedback_tag=str(payload.get("rule_feedback_tag") or ""),
        reviewed_at=reviewed_at,
    )


def human_review_feedback_to_dict(feedback: HumanReviewFeedback) -> dict[str, Any]:
    return asdict(feedback)


def build_human_review_report(
    *,
    provider: str,
    generated_at: datetime,
    review_payload: dict[str, Any],
    feedback_items: list[HumanReviewFeedback],
) -> dict[str, Any]:
    review_items = _review_items_by_ref(review_payload)
    matched: list[tuple[dict[str, Any], HumanReviewFeedback]] = []
    unmatched_feedback: list[str] = []

    for feedback in feedback_items:
        item = review_items.get(feedback.item_ref)
        if item is None:
            unmatched_feedback.append(feedback.item_ref)
            continue
        matched.append((item, feedback))

    agreement_count = 0
    disagreement_count = 0
    per_origin = _group_seed()
    per_classification = _group_seed()
    error_counts = {"false_keep": 0, "false_drop": 0, "weak_mismatch": 0}
    query_disagreements: dict[str, int] = {}
    tag_counts: dict[str, int] = {}

    for item, feedback in matched:
        automatic_label = str(item.get("discovery_decision") or "drop")
        human_label = feedback.human_label
        origin = str(item.get("query_origin") or "unknown")
        classification = str(item.get("classification") or "unknown")
        query = str(item.get("query") or "")
        agreed = automatic_label == human_label

        if agreed:
            agreement_count += 1
        else:
            disagreement_count += 1
            query_disagreements[query] = query_disagreements.get(query, 0) + 1
            error_counts[_error_type(automatic_label, human_label)] += 1
            if feedback.rule_feedback_tag:
                tag_counts[feedback.rule_feedback_tag] = (
                    tag_counts.get(feedback.rule_feedback_tag, 0) + 1
                )

        _record_group(per_origin, origin, agreed=agreed)
        _record_group(per_classification, classification, agreed=agreed)

    return {
        "provider": provider,
        "generated_at": generated_at.isoformat(),
        "review_artifact_generated_at": review_payload.get("generated_at", ""),
        "reviewed_item_count": len(feedback_items),
        "matched_item_count": len(matched),
        "unmatched_item_refs": unmatched_feedback[:20],
        "agreement_count": agreement_count,
        "disagreement_count": disagreement_count,
        "agreement_rate": _rate(agreement_count, len(matched)),
        "per_origin_disagreement_counts": _finalize_group_counts(per_origin),
        "per_classification_disagreement_counts": _finalize_group_counts(per_classification),
        "error_counts": error_counts,
        "rule_feedback_tag_counts": dict(sorted(tag_counts.items())),
        "repeated_query_disagreements": _top_counts(query_disagreements),
        "calibration_assist": build_calibration_assist(
            per_origin=per_origin,
            per_classification=per_classification,
            error_counts=error_counts,
            query_disagreements=query_disagreements,
            tag_counts=tag_counts,
        ),
    }


def build_calibration_assist(
    *,
    per_origin: dict[str, dict[str, int]],
    per_classification: dict[str, dict[str, int]],
    error_counts: dict[str, int],
    query_disagreements: dict[str, int],
    tag_counts: dict[str, int],
) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for origin, counts in sorted(per_origin.items()):
        _append_group_hint(
            hints,
            scope="origin",
            key=origin,
            counts=counts,
            message=f"{origin} origin has elevated human disagreement",
        )
    for classification, counts in sorted(per_classification.items()):
        _append_group_hint(
            hints,
            scope="classification",
            key=classification,
            counts=counts,
            message=f"{classification} classification has elevated human disagreement",
        )
    if error_counts.get("false_keep", 0) > 0:
        hints.append(
            {
                "type": "false_keep_attention",
                "count": error_counts["false_keep"],
                "message": "Automatic rules kept items that humans marked as drop",
            }
        )
    if error_counts.get("false_drop", 0) > 0:
        hints.append(
            {
                "type": "false_drop_attention",
                "count": error_counts["false_drop"],
                "message": "Automatic rules dropped items that humans marked as keep or weak_keep",
            }
        )
    for query, count in _top_counts(query_disagreements, limit=5):
        if count >= 2:
            hints.append(
                {
                    "type": "repeated_query_disagreement",
                    "query": query,
                    "count": count,
                    "message": "Query repeatedly disagreed with human labels",
                }
            )
    for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:5]:
        hints.append(
            {
                "type": "reviewer_feedback_tag",
                "tag": tag,
                "count": count,
                "message": "Reviewer supplied repeated tuning feedback tag",
            }
        )
    return hints


def _review_items_by_ref(review_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = review_payload.get("items")
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_ref = str(item.get("review_item_id") or build_review_item_id(item))
        result[item_ref] = item
    return result


def _error_type(automatic_label: str, human_label: str) -> str:
    if automatic_label != "drop" and human_label == "drop":
        return "false_keep"
    if automatic_label == "drop" and human_label != "drop":
        return "false_drop"
    return "weak_mismatch"


def _group_seed() -> dict[str, dict[str, int]]:
    return {}


def _record_group(groups: dict[str, dict[str, int]], key: str, *, agreed: bool) -> None:
    counts = groups.setdefault(key, {"agreement": 0, "disagreement": 0})
    if agreed:
        counts["agreement"] += 1
    else:
        counts["disagreement"] += 1


def _finalize_group_counts(groups: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for key, counts in sorted(groups.items()):
        total = counts["agreement"] + counts["disagreement"]
        result[key] = {
            "agreement": counts["agreement"],
            "disagreement": counts["disagreement"],
            "reviewed": total,
            "disagreement_rate": _rate(counts["disagreement"], total),
        }
    return result


def _append_group_hint(
    hints: list[dict[str, Any]],
    *,
    scope: str,
    key: str,
    counts: dict[str, int],
    message: str,
) -> None:
    total = counts["agreement"] + counts["disagreement"]
    disagreement_rate = _rate(counts["disagreement"], total)
    if counts["disagreement"] > 0 and (counts["disagreement"] >= 2 or disagreement_rate >= 0.5):
        hints.append(
            {
                "type": f"{scope}_high_disagreement",
                scope: key,
                "disagreement": counts["disagreement"],
                "reviewed": total,
                "disagreement_rate": disagreement_rate,
                "message": message,
            }
        )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _top_counts(counts: dict[str, int], *, limit: int = 10) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
