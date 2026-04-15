from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
)
from src.ingestion.discovery.human_review import feedback_from_import_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import discovery human review feedback")
    parser.add_argument("--provider", default="naver_news")
    parser.add_argument(
        "--directory",
        default=".local/trends-analyzer/discovery_reviews",
        help="Directory containing human review feedback files",
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--format", choices=["csv", "jsonl"], default="csv")
    parser.add_argument("--reviewed-at", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--session-tag", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-output", default="")
    args = parser.parse_args(argv)

    reviewed_at = args.reviewed_at or datetime.now().astimezone().isoformat()
    repository = JsonlDiscoveryHumanReviewRepository(directory=Path(args.directory))
    result = import_feedback_rows(
        repository=repository,
        provider=args.provider,
        rows=read_import_rows(path=Path(args.input), file_format=args.format),
        reviewed_at=reviewed_at,
        reviewer=args.reviewer,
        session_tag=args.session_tag,
        dry_run=args.dry_run,
    )
    if args.summary_output:
        write_summary(path=Path(args.summary_output), payload=result)
    action = "dry_run" if args.dry_run else "imported"
    print(
        f"{action} imported={result['imported_count']} "
        f"skipped={result['skipped_count']} invalid={result['invalid_count']}"
    )
    if result["invalid_samples"]:
        print(f"invalid_samples={result['invalid_samples']}")
    return 0


def import_feedback_rows(
    *,
    repository: JsonlDiscoveryHumanReviewRepository,
    provider: str,
    rows: list[dict[str, Any]],
    reviewed_at: str,
    reviewer: str = "",
    session_tag: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    imported_count = 0
    skipped_count = 0
    invalid_count = 0
    invalid_samples: list[str] = []

    for index, row in enumerate(rows, start=1):
        human_label = str(row.get("human_label") or "").strip()
        if not human_label:
            skipped_count += 1
            continue
        try:
            feedback = feedback_from_import_row(
                row,
                reviewed_at=reviewed_at,
                reviewer=reviewer,
                session_tag=session_tag,
            )
        except ValueError as exc:
            invalid_count += 1
            if len(invalid_samples) < 5:
                invalid_samples.append(f"row={index} error={exc}")
            continue
        if not dry_run:
            repository.append_feedback_sync(provider=provider, feedback=feedback)
        imported_count += 1

    return {
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "invalid_count": invalid_count,
        "invalid_samples": invalid_samples,
        "dry_run": dry_run,
    }


def read_import_rows(*, path: Path, file_format: str) -> list[dict[str, Any]]:
    if file_format == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return [dict(row) for row in csv.DictReader(file)]
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def write_summary(*, path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
