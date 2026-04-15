from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
    load_review_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate discovery human review report")
    parser.add_argument("--provider", default="naver_news")
    parser.add_argument(
        "--directory",
        default=".local/trends-analyzer/discovery_reviews",
        help="Directory containing discovery review artifacts and feedback files",
    )
    parser.add_argument(
        "--review-path",
        default="",
        help="Review artifact path. Defaults to latest_{provider}_review.json in directory",
    )
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    review_path = (
        Path(args.review_path)
        if args.review_path
        else directory / f"latest_{args.provider}_review.json"
    )
    repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
    report = repository.save_report_sync(
        provider=args.provider,
        generated_at=datetime.now().astimezone(),
        review_payload=load_review_artifact(review_path),
    )
    latest_path = directory / f"latest_{args.provider}_human_review_report.json"
    print(f"saved {latest_path}")
    if args.summary:
        print(format_compact_summary(report))
    return 0


def format_compact_summary(report: dict[str, Any]) -> str:
    lines = [
        (
            "summary "
            f"provider={report.get('provider', '')} "
            f"matched={report.get('matched_item_count', 0)} "
            f"agreement={report.get('agreement_count', 0)} "
            f"disagreement={report.get('disagreement_count', 0)} "
            f"agreement_rate={report.get('agreement_rate', 0.0)}"
        ),
        (
            "duplicates "
            f"duplicate_feedback={report.get('duplicate_feedback_count', 0)} "
            f"overwritten_item_refs={report.get('overwritten_item_ref_count', 0)}"
        ),
    ]
    error_counts = report.get("error_counts")
    if isinstance(error_counts, dict):
        lines.append(
            "errors "
            f"false_keep={error_counts.get('false_keep', 0)} "
            f"false_drop={error_counts.get('false_drop', 0)} "
            f"weak_mismatch={error_counts.get('weak_mismatch', 0)}"
        )
    assist = report.get("calibration_assist")
    if isinstance(assist, list) and assist:
        first_hint = assist[0]
        if isinstance(first_hint, dict):
            lines.append(
                "top_hint "
                f"type={first_hint.get('type', '')} "
                f"next_action={first_hint.get('next_action', '')}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
