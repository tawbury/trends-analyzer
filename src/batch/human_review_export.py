from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from src.db.repositories.discovery_human_review_repository import load_review_artifact
from src.ingestion.discovery.human_review import REVIEW_QUEUE_FIELDS, review_item_to_queue_row


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
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    review_path = (
        Path(args.review_path)
        if args.review_path
        else directory / f"latest_{args.provider}_review.json"
    )
    rows = build_review_queue_rows(
        review_payload=load_review_artifact(review_path),
        max_items=args.max_items,
        discovery_decision=args.discovery_decision,
        query_origin=args.query_origin,
        classification=args.classification,
        suspicious_only=args.suspicious_only,
    )
    output_path = Path(args.output)
    if args.format == "csv":
        write_queue_csv(path=output_path, rows=rows)
    else:
        write_queue_jsonl(path=output_path, rows=rows)
    print(f"exported count={len(rows)} path={output_path}")
    return 0


def build_review_queue_rows(
    *,
    review_payload: dict[str, Any],
    max_items: int = 0,
    discovery_decision: str = "",
    query_origin: str = "",
    classification: str = "",
    suspicious_only: bool = False,
) -> list[dict[str, str]]:
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
        rows.append(review_item_to_queue_row(item))
        if max_items > 0 and len(rows) >= max_items:
            break
    return rows


def write_queue_csv(*, path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_queue_jsonl(*, path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(1)
