from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
)
from src.ingestion.discovery.human_review import HumanReviewFeedback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append discovery human review feedback")
    parser.add_argument("--provider", default="naver_news")
    parser.add_argument(
        "--directory",
        default=".local/trends-analyzer/discovery_reviews",
        help="Directory containing discovery review artifacts and feedback files",
    )
    parser.add_argument("--item-ref", required=True)
    parser.add_argument("--human-label", required=True, choices=["keep", "weak_keep", "drop"])
    parser.add_argument("--note", default="")
    parser.add_argument("--rule-feedback-tag", default="")
    parser.add_argument("--reviewed-at", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--session-tag", default="")
    args = parser.parse_args(argv)

    reviewed_at = args.reviewed_at or datetime.now().astimezone().isoformat()
    repository = JsonlDiscoveryHumanReviewRepository(directory=Path(args.directory))
    feedback = HumanReviewFeedback(
        item_ref=args.item_ref,
        human_label=args.human_label,
        note=args.note,
        rule_feedback_tag=args.rule_feedback_tag,
        reviewed_at=reviewed_at,
        reviewer=args.reviewer,
        session_tag=args.session_tag,
    )
    repository.append_feedback_sync(provider=args.provider, feedback=feedback)
    print(
        "appended "
        f"provider={args.provider} item_ref={args.item_ref} "
        f"human_label={args.human_label} reviewed_at={reviewed_at}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
