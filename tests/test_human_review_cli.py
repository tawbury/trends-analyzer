from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from src.batch.human_review_append import main as append_main
from src.batch.human_review_report import main as report_main
from src.ingestion.discovery.review import DiscoveryReviewItem, build_review_item_id


class HumanReviewCliTest(unittest.TestCase):
    def test_append_and_report_cli_use_local_files(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        review_item = _review_item()
        review_path = directory / "latest_naver_news_review.json"
        review_path.write_text(
            json.dumps(
                {
                    "provider": "naver_news",
                    "generated_at": "2026-04-15T16:10:00+09:00",
                    "items": [review_item.__dict__],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        append_output = io.StringIO()
        with redirect_stdout(append_output):
            exit_code = append_main(
                [
                    "--directory",
                    str(directory),
                    "--item-ref",
                    review_item.review_item_id,
                    "--human-label",
                    "drop",
                    "--rule-feedback-tag",
                    "alias_noise",
                    "--reviewer",
                    "operator-a",
                    "--session-tag",
                    "session-1",
                    "--reviewed-at",
                    "2026-04-15T18:00:00+09:00",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("appended provider=naver_news", append_output.getvalue())
        feedback_path = directory / "naver_news_human_feedback.jsonl"
        feedback_payload = json.loads(feedback_path.read_text(encoding="utf-8").strip())
        self.assertEqual(feedback_payload["reviewer"], "operator-a")
        self.assertEqual(feedback_payload["session_tag"], "session-1")

        report_output = io.StringIO()
        with redirect_stdout(report_output):
            exit_code = report_main(["--directory", str(directory), "--summary"])

        self.assertEqual(exit_code, 0)
        output = report_output.getvalue()
        self.assertIn("saved", output)
        self.assertIn("summary provider=naver_news", output)
        self.assertIn("duplicates duplicate_feedback=0", output)

        report_path = directory / "latest_naver_news_human_review_report.json"
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report_payload["matched_item_count"], 1)
        self.assertEqual(report_payload["reviewer_counts"], {"operator-a": 1})
        self.assertEqual(report_payload["session_tag_counts"], {"session-1": 1})


def _review_item() -> DiscoveryReviewItem:
    item = DiscoveryReviewItem(
        symbol="005930",
        query="삼전",
        query_origin="alias",
        title="삼전 특징주",
        url="https://example.com/a",
        published_at="2026-04-15T16:10:00+09:00",
        discovery_decision="keep",
        discovery_score=0.8,
        discovery_reasons=[],
        discovery_suspicious=False,
        classification="stock",
    )
    return DiscoveryReviewItem(
        **{
            **item.__dict__,
            "review_item_id": build_review_item_id(item),
        }
    )


if __name__ == "__main__":
    unittest.main()
