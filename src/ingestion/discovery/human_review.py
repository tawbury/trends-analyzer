from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from src.ingestion.discovery.review import build_review_item_id

DISCOVERY_LABELS = {"keep", "weak_keep", "drop"}

REVIEW_QUEUE_FIELDS = [
    "review_item_id",
    "already_reviewed",
    "latest_human_label",
    "latest_rule_feedback_tag",
    "latest_note",
    "latest_reviewed_at",
    "latest_reviewer",
    "latest_session_tag",
    "priority_score",
    "reason_count",
    "matched_signals",
    "rereview_reason",
    "disagreement_scope",
    "disagreement_metric",
    "symbol",
    "query",
    "query_origin",
    "classification",
    "discovery_decision",
    "discovery_score",
    "title",
    "url",
    "published_at",
    "human_label",
    "note",
    "rule_feedback_tag",
]


@dataclass(frozen=True)
class HumanReviewFeedback:
    item_ref: str
    human_label: str
    note: str = ""
    rule_feedback_tag: str = ""
    reviewed_at: str = ""
    reviewer: str = ""
    session_tag: str = ""


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
        reviewer=str(payload.get("reviewer") or ""),
        session_tag=str(payload.get("session_tag") or ""),
    )


def human_review_feedback_to_dict(feedback: HumanReviewFeedback) -> dict[str, Any]:
    return asdict(feedback)


def review_item_to_queue_row(
    item: dict[str, Any],
    *,
    latest_feedback: HumanReviewFeedback | None = None,
) -> dict[str, str]:
    item_ref = str(item.get("review_item_id") or build_review_item_id(item))
    return {
        "review_item_id": item_ref,
        "already_reviewed": "true" if latest_feedback is not None else "false",
        "latest_human_label": latest_feedback.human_label if latest_feedback else "",
        "latest_rule_feedback_tag": latest_feedback.rule_feedback_tag if latest_feedback else "",
        "latest_note": latest_feedback.note if latest_feedback else "",
        "latest_reviewed_at": latest_feedback.reviewed_at if latest_feedback else "",
        "latest_reviewer": latest_feedback.reviewer if latest_feedback else "",
        "latest_session_tag": latest_feedback.session_tag if latest_feedback else "",
        "priority_score": "0",
        "reason_count": "0",
        "matched_signals": "",
        "rereview_reason": "",
        "disagreement_scope": "",
        "disagreement_metric": "",
        "symbol": str(item.get("symbol") or ""),
        "query": str(item.get("query") or ""),
        "query_origin": str(item.get("query_origin") or ""),
        "classification": str(item.get("classification") or ""),
        "discovery_decision": str(item.get("discovery_decision") or ""),
        "discovery_score": str(item.get("discovery_score") or ""),
        "title": str(item.get("title") or ""),
        "url": str(item.get("url") or ""),
        "published_at": str(item.get("published_at") or ""),
        "human_label": "",
        "note": "",
        "rule_feedback_tag": "",
    }


def feedback_from_import_row(
    row: dict[str, Any],
    *,
    reviewed_at: str,
    reviewer: str = "",
    session_tag: str = "",
) -> HumanReviewFeedback:
    payload = {
        "item_ref": row.get("item_ref") or row.get("review_item_id"),
        "human_label": row.get("human_label"),
        "note": row.get("note", ""),
        "rule_feedback_tag": row.get("rule_feedback_tag", ""),
        "reviewed_at": row.get("reviewed_at") or reviewed_at,
        "reviewer": row.get("reviewer") or reviewer,
        "session_tag": row.get("session_tag") or session_tag,
    }
    return human_review_feedback_from_dict(payload)


def build_human_review_report(
    *,
    provider: str,
    generated_at: datetime,
    review_payload: dict[str, Any],
    feedback_items: list[HumanReviewFeedback],
) -> dict[str, Any]:
    review_items = _review_items_by_ref(review_payload)
    resolved_feedback, duplicate_stats = resolve_latest_feedback(feedback_items)
    matched: list[tuple[dict[str, Any], HumanReviewFeedback]] = []
    unmatched_feedback: list[str] = []

    for feedback in resolved_feedback:
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
    error_samples: dict[str, list[dict[str, str]]] = {
        "false_keep": [],
        "false_drop": [],
        "weak_mismatch": [],
    }
    query_disagreements: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    reviewer_counts: dict[str, int] = {}
    session_tag_counts: dict[str, int] = {}

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
            error_type = _error_type(automatic_label, human_label)
            error_counts[error_type] += 1
            _append_error_sample(
                error_samples[error_type],
                item=item,
                feedback=feedback,
                automatic_label=automatic_label,
                human_label=human_label,
            )
            if feedback.rule_feedback_tag:
                tag_counts[feedback.rule_feedback_tag] = (
                    tag_counts.get(feedback.rule_feedback_tag, 0) + 1
                )

        if feedback.reviewer:
            reviewer_counts[feedback.reviewer] = reviewer_counts.get(feedback.reviewer, 0) + 1
        if feedback.session_tag:
            session_tag_counts[feedback.session_tag] = (
                session_tag_counts.get(feedback.session_tag, 0) + 1
            )
        _record_group(per_origin, origin, agreed=agreed)
        _record_group(per_classification, classification, agreed=agreed)

    return {
        "provider": provider,
        "generated_at": generated_at.isoformat(),
        "review_artifact_generated_at": review_payload.get("generated_at", ""),
        "reviewed_item_count": len(feedback_items),
        "resolved_reviewed_item_count": len(resolved_feedback),
        "matched_item_count": len(matched),
        "unmatched_item_refs": unmatched_feedback[:20],
        "resolution_policy": "latest_wins_by_item_ref",
        "duplicate_feedback_count": duplicate_stats["duplicate_feedback_count"],
        "overwritten_item_ref_count": duplicate_stats["overwritten_item_ref_count"],
        "overwritten_item_refs": duplicate_stats["overwritten_item_refs"],
        "agreement_count": agreement_count,
        "disagreement_count": disagreement_count,
        "agreement_rate": _rate(agreement_count, len(matched)),
        "per_origin_disagreement_counts": _finalize_group_counts(per_origin),
        "per_classification_disagreement_counts": _finalize_group_counts(per_classification),
        "error_counts": error_counts,
        "error_samples": error_samples,
        "rule_feedback_tag_counts": dict(sorted(tag_counts.items())),
        "reviewer_counts": dict(sorted(reviewer_counts.items())),
        "session_tag_counts": dict(sorted(session_tag_counts.items())),
        "repeated_query_disagreements": _top_counts(query_disagreements),
        "calibration_assist": build_calibration_assist(
            per_origin=per_origin,
            per_classification=per_classification,
            error_counts=error_counts,
            query_disagreements=query_disagreements,
            tag_counts=tag_counts,
        ),
    }


def resolve_latest_feedback(
    feedback_items: list[HumanReviewFeedback],
) -> tuple[list[HumanReviewFeedback], dict[str, Any]]:
    latest_by_ref: dict[str, HumanReviewFeedback] = {}
    duplicate_refs: set[str] = set()
    for feedback in feedback_items:
        if feedback.item_ref in latest_by_ref:
            duplicate_refs.add(feedback.item_ref)
        latest_by_ref[feedback.item_ref] = feedback
    return (
        list(latest_by_ref.values()),
        {
            "duplicate_feedback_count": len(feedback_items) - len(latest_by_ref),
            "overwritten_item_ref_count": len(duplicate_refs),
            "overwritten_item_refs": sorted(duplicate_refs)[:20],
        },
    )


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
                "next_action": "Inspect stricter keep threshold, origin penalty, and noisy query terms",
            }
        )
    if error_counts.get("false_drop", 0) > 0:
        hints.append(
            {
                "type": "false_drop_attention",
                "count": error_counts["false_drop"],
                "message": "Automatic rules dropped items that humans marked as keep or weak_keep",
                "next_action": "Inspect weak_keep threshold, classification override, and exact/token match scoring",
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
                    "next_action": "Inspect whether this query should be removed, penalized, or split into a more specific keyword",
                }
            )
    for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:5]:
        hints.append(
            {
                "type": "reviewer_feedback_tag",
                "tag": tag,
                "count": count,
                "message": "Reviewer supplied repeated tuning feedback tag",
                "next_action": "Group examples with this tag before changing discovery rules",
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


def _append_error_sample(
    samples: list[dict[str, str]],
    *,
    item: dict[str, Any],
    feedback: HumanReviewFeedback,
    automatic_label: str,
    human_label: str,
    limit: int = 5,
) -> None:
    if len(samples) >= limit:
        return
    samples.append(
        {
            "review_item_id": str(item.get("review_item_id") or build_review_item_id(item)),
            "symbol": str(item.get("symbol") or ""),
            "query": str(item.get("query") or ""),
            "query_origin": str(item.get("query_origin") or ""),
            "classification": str(item.get("classification") or ""),
            "automatic_label": automatic_label,
            "human_label": human_label,
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "note": feedback.note,
            "rule_feedback_tag": feedback.rule_feedback_tag,
        }
    )


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
                "next_action": _next_action_for_group(scope=scope, key=key),
            }
        )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _top_counts(counts: dict[str, int], *, limit: int = 10) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]


def _next_action_for_group(*, scope: str, key: str) -> str:
    if scope == "origin" and key == "alias":
        return "Inspect alias origin score adjustment, min_query_length, and noisy alias samples"
    if scope == "origin" and key == "query_keyword":
        return "Inspect query_keyword score adjustment, min_token_count, and repeated noisy query keywords"
    if scope == "classification" and key.lower() in {"etf", "etn", "spac"}:
        return f"Inspect {key} classification keep and weak_keep threshold overrides"
    return f"Inspect {scope}={key} examples before changing discovery rules"
