from __future__ import annotations

import argparse
import csv
import json
import sys
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
    parser.add_argument("--csv-bom", action="store_true")
    args = parser.parse_args(argv)

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
    rows = build_review_queue_rows(
        review_payload=load_review_artifact(review_path),
        latest_feedback_by_ref=latest_feedback_by_ref,
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
    )
    output_path = Path(args.output)
    if args.format == "csv":
        write_queue_csv(path=output_path, rows=rows, bom=args.csv_bom)
    else:
        write_queue_jsonl(path=output_path, rows=rows)
    print(f"exported count={len(rows)} path={output_path}")
    return 0


def build_review_queue_rows(
    *,
    review_payload: dict[str, Any],
    latest_feedback_by_ref: dict[str, HumanReviewFeedback] | None = None,
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
) -> list[dict[str, str]]:
    feedback_by_ref = latest_feedback_by_ref or {}
    noisy_queries = _noisy_queries(review_payload)
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
        if max_items > 0 and len(rows) >= max_items:
            break
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


def latest_feedback_by_item_ref(
    feedback_items: list[HumanReviewFeedback],
) -> dict[str, HumanReviewFeedback]:
    latest_feedback, _ = resolve_latest_feedback(feedback_items)
    return {feedback.item_ref: feedback for feedback in latest_feedback}


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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(1)
