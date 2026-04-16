from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
    load_review_artifact,
)
from src.ingestion.discovery.human_review import (
    REVIEW_QUEUE_FIELDS,
    HumanReviewFeedback,
    resolve_latest_feedback,
    review_item_to_queue_row,
)
from src.ingestion.discovery.review import build_review_item_id


DISAGREEMENT_PRESETS = {
    "disagreement_origin",
    "disagreement_classification",
    "repeated_query_disagreement",
    "false_keep_focus",
    "false_drop_focus",
}
ASSIST_PRESETS = {
    "origin_high_disagreement",
    "classification_high_disagreement",
    "repeated_query_disagreement",
}
QUEUE_SIGNALS = {
    "weak_keep",
    "suspicious",
    "noisy",
    "reviewed_drop",
    "reviewed_weak_keep",
}
PRIORITY_WEIGHTS = {
    "false_keep_focus": 100,
    "false_drop_focus": 100,
    "repeated_query_disagreement": 75,
    "assist_repeated_query_disagreement": 70,
    "origin_disagreement": 60,
    "classification_disagreement": 60,
    "assist_origin_high_disagreement": 55,
    "assist_classification_high_disagreement": 55,
    "suspicious_focus": 40,
    "reviewed_drop_focus": 35,
    "noisy_query_focus": 30,
    "reviewed_weak_keep_focus": 25,
    "weak_keep_focus": 20,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export discovery human review queue")
    parser.add_argument("--provider", default="naver_news")
    parser.add_argument(
        "--directory",
        default=".local/trends-analyzer/discovery_reviews",
        help="Directory containing discovery review artifacts",
    )
    parser.add_argument(
        "--review-path",
        default="",
        help="Review artifact path. Defaults to latest_{provider}_review.json in directory",
    )
    parser.add_argument(
        "--human-review-report-path",
        default="",
        help="Human review report path. Defaults to latest_{provider}_human_review_report.json when a disagreement preset is used",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=["csv", "jsonl"], default="csv")
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--discovery-decision", default="")
    parser.add_argument("--query-origin", default="")
    parser.add_argument("--classification", default="")
    parser.add_argument("--suspicious-only", action="store_true")
    parser.add_argument("--exclude-reviewed", action="store_true")
    parser.add_argument("--unreviewed-only", action="store_true")
    parser.add_argument("--reviewed-only", action="store_true")
    parser.add_argument("--latest-human-label", default="")
    parser.add_argument("--latest-reviewer", default="")
    parser.add_argument("--latest-session-tag", default="")
    parser.add_argument("--latest-rule-feedback-tag", default="")
    parser.add_argument("--noisy-query-only", action="store_true")
    parser.add_argument(
        "--priority",
        choices=["", "weak_keep", "suspicious", "noisy", "reviewed_drop", "reviewed_weak_keep"],
        default="",
    )
    parser.add_argument(
        "--disagreement-preset",
        action="append",
        default=[],
        help=(
            "Disagreement preset. Repeat the flag or use comma-separated values. "
            "Allowed: disagreement_origin, disagreement_classification, "
            "repeated_query_disagreement, false_keep_focus, false_drop_focus"
        ),
    )
    parser.add_argument(
        "--assist-preset",
        action="append",
        default=[],
        help=(
            "Calibration assist preset. Repeat the flag or use comma-separated values. "
            "Allowed: origin_high_disagreement, classification_high_disagreement, "
            "repeated_query_disagreement"
        ),
    )
    parser.add_argument(
        "--queue-signal",
        action="append",
        default=[],
        help=(
            "Review artifact signal to OR with report-driven presets. "
            "Repeat the flag or use comma-separated values. "
            "Allowed: weak_keep, suspicious, noisy, reviewed_drop, reviewed_weak_keep"
        ),
    )
    parser.add_argument("--min-disagreement-count", type=int, default=1)
    parser.add_argument("--min-disagreement-rate", type=float, default=0.0)
    parser.add_argument("--min-query-disagreement-count", type=int, default=2)
    parser.add_argument("--csv-bom", action="store_true")
    parser.add_argument(
        "--summary-output",
        default="",
        help="Optional JSON path for a compact queue export manifest and composition summary",
    )
    args = parser.parse_args(argv)
    disagreement_presets = _parse_signal_values(
        "disagreement-preset",
        args.disagreement_preset,
        allowed_values=DISAGREEMENT_PRESETS,
    )
    assist_presets = _parse_signal_values(
        "assist-preset",
        args.assist_preset,
        allowed_values=ASSIST_PRESETS,
    )
    queue_signals = _parse_signal_values(
        "queue-signal",
        args.queue_signal,
        allowed_values=QUEUE_SIGNALS,
    )

    directory = Path(args.directory)
    review_path = (
        Path(args.review_path)
        if args.review_path
        else directory / f"latest_{args.provider}_review.json"
    )
    repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
    latest_feedback_by_ref = latest_feedback_by_item_ref(
        repository.list_feedback_sync(provider=args.provider)
    )
    human_review_report = None
    human_review_report_path = ""
    if disagreement_presets or assist_presets:
        report_path = (
            Path(args.human_review_report_path)
            if args.human_review_report_path
            else directory / f"latest_{args.provider}_human_review_report.json"
        )
        human_review_report_path = str(report_path)
        human_review_report = load_review_artifact(report_path)
    queue_signals = queue_signals + _priority_queue_signals(args.priority)
    rows = build_review_queue_rows(
        review_payload=load_review_artifact(review_path),
        latest_feedback_by_ref=latest_feedback_by_ref,
        human_review_report=human_review_report,
        max_items=args.max_items,
        discovery_decision=args.discovery_decision or _priority_discovery_decision(args.priority),
        query_origin=args.query_origin,
        classification=args.classification,
        suspicious_only=args.suspicious_only or args.priority == "suspicious",
        exclude_reviewed=args.exclude_reviewed or args.unreviewed_only,
        reviewed_only=args.reviewed_only,
        latest_human_label=args.latest_human_label
        or _priority_latest_human_label(args.priority),
        latest_reviewer=args.latest_reviewer,
        latest_session_tag=args.latest_session_tag,
        latest_rule_feedback_tag=args.latest_rule_feedback_tag,
        noisy_query_only=args.noisy_query_only or args.priority == "noisy",
        disagreement_preset=disagreement_presets,
        assist_preset=assist_presets,
        queue_signal=queue_signals,
        min_disagreement_count=args.min_disagreement_count,
        min_disagreement_rate=args.min_disagreement_rate,
        min_query_disagreement_count=args.min_query_disagreement_count,
    )
    output_path = Path(args.output)
    if args.format == "csv":
        write_queue_csv(path=output_path, rows=rows, bom=args.csv_bom)
    else:
        write_queue_jsonl(path=output_path, rows=rows)
    if args.summary_output:
        summary = build_queue_export_summary(
            provider=args.provider,
            review_path=str(review_path),
            human_review_report_path=human_review_report_path,
            output_path=str(output_path),
            output_format=args.format,
            disagreement_presets=disagreement_presets,
            assist_presets=assist_presets,
            queue_signals=queue_signals,
            rows=rows,
            filters={
                "max_items": args.max_items,
                "discovery_decision": args.discovery_decision
                or _priority_discovery_decision(args.priority),
                "query_origin": args.query_origin,
                "classification": args.classification,
                "suspicious_only": args.suspicious_only or args.priority == "suspicious",
                "exclude_reviewed": args.exclude_reviewed or args.unreviewed_only,
                "unreviewed_only": args.unreviewed_only,
                "reviewed_only": args.reviewed_only,
                "latest_human_label": args.latest_human_label
                or _priority_latest_human_label(args.priority),
                "latest_reviewer": args.latest_reviewer,
                "latest_session_tag": args.latest_session_tag,
                "latest_rule_feedback_tag": args.latest_rule_feedback_tag,
                "noisy_query_only": args.noisy_query_only or args.priority == "noisy",
                "priority": args.priority,
                "min_disagreement_count": args.min_disagreement_count,
                "min_disagreement_rate": args.min_disagreement_rate,
                "min_query_disagreement_count": args.min_query_disagreement_count,
            },
        )
        write_queue_summary(path=Path(args.summary_output), summary=summary)
    print(f"exported count={len(rows)} path={output_path}")
    return 0


def build_review_queue_rows(
    *,
    review_payload: dict[str, Any],
    latest_feedback_by_ref: dict[str, HumanReviewFeedback] | None = None,
    human_review_report: dict[str, Any] | None = None,
    max_items: int = 0,
    discovery_decision: str = "",
    query_origin: str = "",
    classification: str = "",
    suspicious_only: bool = False,
    exclude_reviewed: bool = False,
    reviewed_only: bool = False,
    latest_human_label: str = "",
    latest_reviewer: str = "",
    latest_session_tag: str = "",
    latest_rule_feedback_tag: str = "",
    noisy_query_only: bool = False,
    disagreement_preset: str | list[str] = "",
    assist_preset: str | list[str] = "",
    queue_signal: str | list[str] = "",
    min_disagreement_count: int = 1,
    min_disagreement_rate: float = 0.0,
    min_query_disagreement_count: int = 2,
) -> list[dict[str, str]]:
    feedback_by_ref = latest_feedback_by_ref or {}
    noisy_queries = _noisy_queries(review_payload)
    disagreement_presets = _normalize_signal_values(disagreement_preset)
    assist_presets = _normalize_signal_values(assist_preset)
    queue_signals = _normalize_signal_values(queue_signal)
    multi_signal_active = bool(disagreement_presets or assist_presets or queue_signals)
    disagreement_signal = _build_disagreement_signal(
        report=human_review_report,
        presets=disagreement_presets,
        assist_presets=assist_presets,
        min_disagreement_count=min_disagreement_count,
        min_disagreement_rate=min_disagreement_rate,
        min_query_disagreement_count=min_query_disagreement_count,
    )
    items = review_payload.get("items")
    if not isinstance(items, list):
        return []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if discovery_decision and item.get("discovery_decision") != discovery_decision:
            continue
        if query_origin and item.get("query_origin") != query_origin:
            continue
        if classification and item.get("classification") != classification:
            continue
        if suspicious_only and not bool(item.get("discovery_suspicious")):
            continue
        if noisy_query_only and str(item.get("query") or "") not in noisy_queries:
            continue
        item_ref = str(item.get("review_item_id") or build_review_item_id(item))
        row = review_item_to_queue_row(item, latest_feedback=feedback_by_ref.get(item_ref))
        if multi_signal_active:
            reasons = _queue_signal_reasons(
                item=item,
                row=row,
                noisy_queries=noisy_queries,
                signals=queue_signals,
            )
            reasons.extend(_disagreement_reasons(item=item, row=row, signal=disagreement_signal))
            if not reasons:
                continue
            row.update(_combine_reasons(reasons))
        if exclude_reviewed and row["already_reviewed"] == "true":
            continue
        if reviewed_only and row["already_reviewed"] != "true":
            continue
        if latest_human_label and row["latest_human_label"] != latest_human_label:
            continue
        if latest_reviewer and row["latest_reviewer"] != latest_reviewer:
            continue
        if latest_session_tag and row["latest_session_tag"] != latest_session_tag:
            continue
        if latest_rule_feedback_tag and row["latest_rule_feedback_tag"] != latest_rule_feedback_tag:
            continue
        rows.append(row)
    rows.sort(key=_queue_row_sort_key)
    if max_items > 0:
        return rows[:max_items]
    return rows


def write_queue_csv(*, path: Path, rows: list[dict[str, str]], bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_queue_jsonl(*, path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def write_queue_summary(*, path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_queue_export_summary(
    *,
    provider: str,
    review_path: str,
    human_review_report_path: str,
    output_path: str,
    output_format: str,
    disagreement_presets: list[str],
    assist_presets: list[str],
    queue_signals: list[str],
    filters: dict[str, Any],
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    reviewed_count = sum(1 for row in rows if row.get("already_reviewed") == "true")
    matched_signal_counts = _count_split_values(rows, "matched_signals")
    rereview_reason_counts = _count_values(rows, "rereview_reason")
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "provider": provider,
        "review_path": review_path,
        "human_review_report_path": human_review_report_path,
        "applied_disagreement_presets": disagreement_presets,
        "applied_assist_presets": assist_presets,
        "applied_queue_signals": queue_signals,
        "applied_filters": filters,
        "output_path": output_path,
        "output_format": output_format,
        "selected_count": len(rows),
        "reviewed_count": reviewed_count,
        "unreviewed_count": len(rows) - reviewed_count,
        "matched_signal_counts": matched_signal_counts,
        "rereview_reason_counts": rereview_reason_counts,
        "top_matched_signals": _top_counts(matched_signal_counts, limit=10),
        "priority_score_buckets": _priority_score_buckets(rows),
        "top_priority_row_samples": _top_priority_row_samples(rows, limit=5),
    }


def latest_feedback_by_item_ref(
    feedback_items: list[HumanReviewFeedback],
) -> dict[str, HumanReviewFeedback]:
    latest_feedback, _ = resolve_latest_feedback(feedback_items)
    return {feedback.item_ref: feedback for feedback in latest_feedback}


def _build_disagreement_signal(
    *,
    report: dict[str, Any] | None,
    presets: list[str],
    assist_presets: list[str],
    min_disagreement_count: int,
    min_disagreement_rate: float,
    min_query_disagreement_count: int,
) -> dict[str, Any]:
    if not presets and not assist_presets:
        return {}
    if report is None:
        raise ValueError("Human review report is required for disagreement-aware export")
    assist_signal = _assist_signal(
        report.get("calibration_assist"),
        assist_presets=assist_presets,
    )
    return {
        "presets": presets,
        "assist_presets": assist_presets,
        "origins": _disagreement_keys(
            report.get("per_origin_disagreement_counts"),
            min_count=min_disagreement_count,
            min_rate=min_disagreement_rate,
        ),
        "classifications": _disagreement_keys(
            report.get("per_classification_disagreement_counts"),
            min_count=min_disagreement_count,
            min_rate=min_disagreement_rate,
        ),
        "queries": _repeated_disagreement_queries(
            report.get("repeated_query_disagreements"),
            min_count=min_query_disagreement_count,
        ),
        "assist_origins": assist_signal["origins"],
        "assist_classifications": assist_signal["classifications"],
        "assist_queries": assist_signal["queries"],
    }


def _assist_signal(values: Any, *, assist_presets: list[str]) -> dict[str, dict[str, str]]:
    signal: dict[str, dict[str, str]] = {
        "origins": {},
        "classifications": {},
        "queries": {},
    }
    if not assist_presets or not isinstance(values, list):
        return signal
    for value in values:
        if not isinstance(value, dict):
            continue
        assist_preset = str(value.get("type") or "")
        if assist_preset not in assist_presets:
            continue
        metric = _assist_metric(value)
        if assist_preset == "origin_high_disagreement" and value.get("origin"):
            signal["origins"][str(value["origin"])] = metric
        if assist_preset == "classification_high_disagreement" and value.get("classification"):
            signal["classifications"][str(value["classification"])] = metric
        if assist_preset == "repeated_query_disagreement" and value.get("query"):
            signal["queries"][str(value["query"])] = metric
    return signal


def _assist_metric(value: dict[str, Any]) -> str:
    parts: list[str] = []
    if "disagreement" in value:
        parts.append(f"disagreement={value['disagreement']}")
    if "disagreement_rate" in value:
        parts.append(f"rate={value['disagreement_rate']}")
    if "count" in value:
        parts.append(f"count={value['count']}")
    return ";".join(parts) or "assist_hint=true"


def _disagreement_keys(
    values: Any,
    *,
    min_count: int,
    min_rate: float,
) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    result: dict[str, str] = {}
    for key, payload in values.items():
        if not isinstance(payload, dict):
            continue
        count = int(payload.get("disagreement") or 0)
        rate = float(payload.get("disagreement_rate") or 0.0)
        if count >= min_count and rate >= min_rate:
            result[str(key)] = f"disagreement={count};rate={rate}"
    return result


def _repeated_disagreement_queries(values: Any, *, min_count: int) -> dict[str, str]:
    if not isinstance(values, list):
        return {}
    result: dict[str, str] = {}
    for value in values:
        query = ""
        count = 0
        if isinstance(value, dict):
            query = str(value.get("query") or "")
            count = int(value.get("count") or 0)
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            query = str(value[0])
            count = int(value[1])
        if query and count >= min_count:
            result[query] = f"disagreement={count}"
    return result


def _disagreement_reasons(
    *,
    item: dict[str, Any],
    row: dict[str, str],
    signal: dict[str, Any],
) -> list[dict[str, str]]:
    if not signal:
        return []
    reasons: list[dict[str, str]] = []
    presets = set(signal.get("presets") or [])
    assist_presets = set(signal.get("assist_presets") or [])
    if "origin_high_disagreement" in assist_presets:
        origin = str(item.get("query_origin") or "")
        metric = signal["assist_origins"].get(origin)
        if metric:
            reasons.append(_reason("assist_origin_high_disagreement", f"origin:{origin}", metric))
    if "classification_high_disagreement" in assist_presets:
        classification = str(item.get("classification") or "")
        metric = signal["assist_classifications"].get(classification)
        if metric:
            reasons.append(
                _reason(
                    "assist_classification_high_disagreement",
                    f"classification:{classification}",
                    metric,
                )
            )
    if "repeated_query_disagreement" in assist_presets:
        query = str(item.get("query") or "")
        metric = signal["assist_queries"].get(query)
        if metric:
            reasons.append(_reason("assist_repeated_query_disagreement", f"query:{query}", metric))
    if "disagreement_origin" in presets:
        origin = str(item.get("query_origin") or "")
        metric = signal["origins"].get(origin)
        if metric:
            reasons.append(_reason("origin_disagreement", f"origin:{origin}", metric))
    if "disagreement_classification" in presets:
        classification = str(item.get("classification") or "")
        metric = signal["classifications"].get(classification)
        if metric:
            reasons.append(
                _reason(
                    "classification_disagreement",
                    f"classification:{classification}",
                    metric,
                )
            )
    if "repeated_query_disagreement" in presets:
        query = str(item.get("query") or "")
        metric = signal["queries"].get(query)
        if metric:
            reasons.append(_reason("repeated_query_disagreement", f"query:{query}", metric))
    if "false_keep_focus" in presets:
        if row["latest_human_label"] == "drop" and row["discovery_decision"] != "drop":
            reasons.append(
                _reason(
                    "false_keep_focus",
                    "error:false_keep",
                    "auto_keep_or_weak_keep;human_drop",
                )
            )
    if "false_drop_focus" in presets:
        if row["latest_human_label"] in {"keep", "weak_keep"} and row["discovery_decision"] == "drop":
            reasons.append(
                _reason(
                    "false_drop_focus",
                    "error:false_drop",
                    "auto_drop;human_keep_or_weak_keep",
                )
            )
    return reasons


def _queue_signal_reasons(
    *,
    item: dict[str, Any],
    row: dict[str, str],
    noisy_queries: set[str],
    signals: list[str],
) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []
    signal_set = set(signals)
    if "weak_keep" in signal_set and item.get("discovery_decision") == "weak_keep":
        reasons.append(_reason("weak_keep_focus", "decision:weak_keep", "auto_weak_keep=true"))
    if "suspicious" in signal_set and bool(item.get("discovery_suspicious")):
        reasons.append(_reason("suspicious_focus", "item:suspicious", "discovery_suspicious=true"))
    query = str(item.get("query") or "")
    if "noisy" in signal_set and query in noisy_queries:
        reasons.append(_reason("noisy_query_focus", f"query:{query}", "noisy_query_sample=true"))
    if "reviewed_drop" in signal_set and row["latest_human_label"] == "drop":
        reasons.append(_reason("reviewed_drop_focus", "human_label:drop", "latest_human_drop=true"))
    if "reviewed_weak_keep" in signal_set and row["latest_human_label"] == "weak_keep":
        reasons.append(
            _reason(
                "reviewed_weak_keep_focus",
                "human_label:weak_keep",
                "latest_human_weak_keep=true",
            )
        )
    return reasons


def _combine_reasons(reasons: list[dict[str, str]]) -> dict[str, str]:
    matched_signals = _unique_values(reason["rereview_reason"] for reason in reasons)
    return {
        "priority_score": str(_priority_score(matched_signals)),
        "reason_count": str(len(matched_signals)),
        "matched_signals": ";".join(matched_signals),
        "rereview_reason": ";".join(matched_signals),
        "disagreement_scope": ";".join(
            _unique_values(reason["disagreement_scope"] for reason in reasons)
        ),
        "disagreement_metric": ";".join(
            _unique_values(reason["disagreement_metric"] for reason in reasons)
        ),
    }


def _unique_values(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in result:
            result.append(text)
    return result


def _priority_score(signals: list[str]) -> int:
    return sum(PRIORITY_WEIGHTS.get(signal, 0) for signal in signals)


def _queue_row_sort_key(row: dict[str, str]) -> int:
    return -int(row.get("priority_score") or 0)


def _count_split_values(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for value in _split_row_values(row.get(key, "")):
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _count_values(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _split_row_values(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def _top_counts(counts: dict[str, int], *, limit: int) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _priority_score_buckets(rows: list[dict[str, str]]) -> dict[str, int]:
    buckets = {
        "0": 0,
        "1_39": 0,
        "40_59": 0,
        "60_99": 0,
        "100_plus": 0,
    }
    for row in rows:
        score = int(row.get("priority_score") or 0)
        if score <= 0:
            buckets["0"] += 1
        elif score < 40:
            buckets["1_39"] += 1
        elif score < 60:
            buckets["40_59"] += 1
        elif score < 100:
            buckets["60_99"] += 1
        else:
            buckets["100_plus"] += 1
    return buckets


def _top_priority_row_samples(rows: list[dict[str, str]], *, limit: int) -> list[dict[str, str]]:
    sample_fields = [
        "review_item_id",
        "priority_score",
        "reason_count",
        "matched_signals",
        "symbol",
        "query",
        "query_origin",
        "classification",
        "discovery_decision",
        "latest_human_label",
        "title",
        "url",
    ]
    return [
        {field: row.get(field, "") for field in sample_fields}
        for row in rows[:limit]
    ]


def _reason(reason: str, scope: str, metric: str) -> dict[str, str]:
    return {
        "rereview_reason": reason,
        "disagreement_scope": scope,
        "disagreement_metric": metric,
    }


def _noisy_queries(review_payload: dict[str, Any]) -> set[str]:
    summary = review_payload.get("calibration_summary")
    if not isinstance(summary, dict):
        return set()
    result: set[str] = set()
    for key in ("noisy_query_sample", "noisy_alias_sample", "noisy_keyword_sample"):
        values = summary.get(key)
        if isinstance(values, list):
            result.update(str(value) for value in values if value)
    return result


def _priority_discovery_decision(priority: str) -> str:
    if priority == "weak_keep":
        return "weak_keep"
    return ""


def _priority_latest_human_label(priority: str) -> str:
    if priority == "reviewed_drop":
        return "drop"
    if priority == "reviewed_weak_keep":
        return "weak_keep"
    return ""


def _priority_queue_signals(priority: str) -> list[str]:
    if priority in QUEUE_SIGNALS:
        return [priority]
    return []


def _parse_signal_values(
    option_name: str,
    values: list[str],
    *,
    allowed_values: set[str],
) -> list[str]:
    result = _normalize_signal_values(values)
    invalid_values = [value for value in result if value not in allowed_values]
    if invalid_values:
        joined_allowed = ", ".join(sorted(allowed_values))
        joined_invalid = ", ".join(invalid_values)
        raise SystemExit(f"invalid --{option_name}: {joined_invalid}. allowed: {joined_allowed}")
    return result


def _normalize_signal_values(value: str | list[str]) -> list[str]:
    raw_values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for raw_value in raw_values:
        for part in str(raw_value or "").split(","):
            normalized = part.strip()
            if normalized and normalized not in result:
                result.append(normalized)
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(1)
