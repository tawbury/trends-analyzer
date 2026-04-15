from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
)
from src.ingestion.discovery.human_review import (
    HumanReviewFeedback,
    build_human_review_report,
    human_review_feedback_from_dict,
)
from src.ingestion.discovery.review import DiscoveryReviewItem, build_review_item_id


class HumanReviewTest(unittest.TestCase):
    def test_feedback_from_dict_accepts_item_ref_and_validates_label(self) -> None:
        feedback = human_review_feedback_from_dict(
            {
                "item_ref": "abc123",
                "human_label": "drop",
                "note": "generic market headline",
                "rule_feedback_tag": "alias_noise",
                "reviewed_at": "2026-04-15T18:00:00+09:00",
            }
        )

        self.assertEqual(feedback.item_ref, "abc123")
        self.assertEqual(feedback.human_label, "drop")
        self.assertEqual(feedback.rule_feedback_tag, "alias_noise")

        with self.assertRaises(ValueError):
            human_review_feedback_from_dict({"item_ref": "abc123", "human_label": "maybe"})

    def test_human_review_report_compares_auto_and_human_labels(self) -> None:
        keep_item = _review_item(
            query="삼성전자",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
        )
        alias_item = _review_item(
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="keep",
        )
        etf_item = _review_item(
            query="테스트ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
        )
        review_payload = _review_payload([keep_item, alias_item, etf_item])

        report = build_human_review_report(
            provider="naver_news",
            generated_at=datetime.fromisoformat("2026-04-15T18:10:00+09:00"),
            review_payload=review_payload,
            feedback_items=[
                HumanReviewFeedback(
                    item_ref=keep_item.review_item_id,
                    human_label="keep",
                    reviewed_at="2026-04-15T18:00:00+09:00",
                ),
                HumanReviewFeedback(
                    item_ref=alias_item.review_item_id,
                    human_label="drop",
                    rule_feedback_tag="alias_noise",
                    reviewed_at="2026-04-15T18:01:00+09:00",
                ),
                HumanReviewFeedback(
                    item_ref=etf_item.review_item_id,
                    human_label="weak_keep",
                    rule_feedback_tag="etf_threshold",
                    reviewed_at="2026-04-15T18:02:00+09:00",
                ),
                HumanReviewFeedback(
                    item_ref="missing",
                    human_label="drop",
                    reviewed_at="2026-04-15T18:03:00+09:00",
                ),
            ],
        )

        self.assertEqual(report["reviewed_item_count"], 4)
        self.assertEqual(report["matched_item_count"], 3)
        self.assertEqual(report["unmatched_item_refs"], ["missing"])
        self.assertEqual(report["agreement_count"], 1)
        self.assertEqual(report["disagreement_count"], 2)
        self.assertEqual(report["error_counts"]["false_keep"], 1)
        self.assertEqual(report["error_counts"]["false_drop"], 1)
        self.assertEqual(
            report["per_origin_disagreement_counts"]["alias"]["disagreement"],
            1,
        )
        self.assertEqual(
            report["per_classification_disagreement_counts"]["etf"]["disagreement"],
            1,
        )
        self.assertIn(
            {
                "type": "false_keep_attention",
                "count": 1,
                "message": "Automatic rules kept items that humans marked as drop",
            },
            report["calibration_assist"],
        )
        self.assertIn(
            {
                "type": "false_drop_attention",
                "count": 1,
                "message": "Automatic rules dropped items that humans marked as keep or weak_keep",
            },
            report["calibration_assist"],
        )

    def test_repository_appends_feedback_and_saves_report(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        review_item = _review_item(
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
        )

        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=review_item.review_item_id,
                human_label="drop",
                note="Alias result is too broad",
                rule_feedback_tag="alias_penalty",
                reviewed_at="2026-04-15T18:20:00+09:00",
            ),
        )

        feedback_items = repository.list_feedback_sync(provider="naver_news")
        self.assertEqual(len(feedback_items), 1)
        self.assertEqual(feedback_items[0].rule_feedback_tag, "alias_penalty")

        report = repository.save_report_sync(
            provider="naver_news",
            generated_at=datetime.fromisoformat("2026-04-15T18:30:00+09:00"),
            review_payload=_review_payload([review_item]),
        )

        self.assertEqual(report["error_counts"]["false_keep"], 1)
        latest_path = directory / "latest_naver_news_human_review_report.json"
        saved = json.loads(latest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["matched_item_count"], 1)


def _review_item(
    *,
    query: str,
    query_origin: str,
    classification: str,
    decision: str,
) -> DiscoveryReviewItem:
    item = DiscoveryReviewItem(
        symbol="005930",
        query=query,
        query_origin=query_origin,
        title=query,
        url=f"https://example.com/{query}",
        published_at="2026-04-15T16:10:00+09:00",
        discovery_decision=decision,
        discovery_score=0.8,
        discovery_reasons=[],
        discovery_suspicious=False,
        classification=classification,
    )
    return DiscoveryReviewItem(
        **{
            **item.__dict__,
            "review_item_id": build_review_item_id(item),
        }
    )


def _review_payload(items: list[DiscoveryReviewItem]) -> dict:
    return {
        "provider": "naver_news",
        "generated_at": "2026-04-15T16:10:00+09:00",
        "items": [item.__dict__ for item in items],
    }


if __name__ == "__main__":
    unittest.main()
