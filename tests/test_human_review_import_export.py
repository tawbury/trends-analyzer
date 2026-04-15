from __future__ import annotations

import csv
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from src.batch.human_review_export import build_review_queue_rows, main as export_main
from src.batch.human_review_import import import_feedback_rows, main as import_main
from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
)
from src.ingestion.discovery.review import DiscoveryReviewItem, build_review_item_id


class HumanReviewImportExportTest(unittest.TestCase):
    def test_build_review_queue_rows_filters_candidates(self) -> None:
        keep_item = _review_item(
            symbol="005930",
            query="삼성전자",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        drop_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=True,
        )

        rows = build_review_queue_rows(
            review_payload=_review_payload([keep_item, drop_item]),
            discovery_decision="drop",
            query_origin="query_keyword",
            classification="etf",
            suspicious_only=True,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_item_id"], drop_item.review_item_id)
        self.assertEqual(rows[0]["human_label"], "")
        self.assertEqual(rows[0]["note"], "")
        self.assertEqual(rows[0]["rule_feedback_tag"], "")

    def test_export_cli_writes_csv_and_jsonl(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        review_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=True,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([review_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        csv_path = directory / "queue.csv"
        jsonl_path = directory / "queue.jsonl"

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(csv_path),
                    "--format",
                    "csv",
                    "--suspicious-only",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("exported count=1", output.getvalue())
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]["review_item_id"], review_item.review_item_id)

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(jsonl_path),
                    "--format",
                    "jsonl",
                    "--max-items",
                    "1",
                ]
            )

        self.assertEqual(exit_code, 0)
        jsonl_row = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
        self.assertEqual(jsonl_row["review_item_id"], review_item.review_item_id)

    def test_import_feedback_rows_counts_imported_skipped_and_invalid(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repository = JsonlDiscoveryHumanReviewRepository(directory=Path(temp_dir.name))

        result = import_feedback_rows(
            repository=repository,
            provider="naver_news",
            rows=[
                {
                    "review_item_id": "item-1",
                    "human_label": "drop",
                    "note": "noisy",
                },
                {
                    "review_item_id": "item-2",
                    "human_label": "",
                },
                {
                    "review_item_id": "item-3",
                    "human_label": "maybe",
                },
            ],
            reviewed_at="2026-04-15T18:00:00+09:00",
            reviewer="operator-a",
            session_tag="batch-1",
        )

        self.assertEqual(result["imported_count"], 1)
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["invalid_count"], 1)
        feedback_items = repository.list_feedback_sync(provider="naver_news")
        self.assertEqual(len(feedback_items), 1)
        self.assertEqual(feedback_items[0].reviewer, "operator-a")
        self.assertEqual(feedback_items[0].session_tag, "batch-1")

    def test_import_cli_reads_labeled_csv(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        input_path = directory / "labeled.csv"
        with input_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "review_item_id",
                    "human_label",
                    "note",
                    "rule_feedback_tag",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "review_item_id": "item-1",
                    "human_label": "weak_keep",
                    "note": "borderline",
                    "rule_feedback_tag": "threshold_review",
                }
            )
            writer.writerow(
                {
                    "review_item_id": "item-2",
                    "human_label": "",
                    "note": "",
                    "rule_feedback_tag": "",
                }
            )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = import_main(
                [
                    "--directory",
                    str(directory),
                    "--input",
                    str(input_path),
                    "--format",
                    "csv",
                    "--reviewed-at",
                    "2026-04-15T18:30:00+09:00",
                    "--reviewer",
                    "operator-a",
                    "--session-tag",
                    "batch-1",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("imported imported=1 skipped=1 invalid=0", output.getvalue())
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        feedback_items = repository.list_feedback_sync(provider="naver_news")
        self.assertEqual(feedback_items[0].human_label, "weak_keep")
        self.assertEqual(feedback_items[0].rule_feedback_tag, "threshold_review")


def _review_item(
    *,
    symbol: str,
    query: str,
    query_origin: str,
    classification: str,
    decision: str,
    suspicious: bool,
) -> DiscoveryReviewItem:
    item = DiscoveryReviewItem(
        symbol=symbol,
        query=query,
        query_origin=query_origin,
        title=query,
        url=f"https://example.com/{symbol}/{query}",
        published_at="2026-04-15T16:10:00+09:00",
        discovery_decision=decision,
        discovery_score=0.8,
        discovery_reasons=[],
        discovery_suspicious=suspicious,
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
