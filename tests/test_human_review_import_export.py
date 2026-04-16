from __future__ import annotations

import csv
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from src.batch.human_review_export import (
    build_review_queue_rows,
    latest_feedback_by_item_ref,
    main as export_main,
)
from src.batch.human_review_import import import_feedback_rows, main as import_main
from src.db.repositories.discovery_human_review_repository import (
    JsonlDiscoveryHumanReviewRepository,
)
from src.ingestion.discovery.human_review import HumanReviewFeedback
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

    def test_build_review_queue_rows_marks_and_excludes_reviewed_items(self) -> None:
        reviewed_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        unresolved_item = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        feedback_items = [
            HumanReviewFeedback(
                item_ref=reviewed_item.review_item_id,
                human_label="keep",
                reviewed_at="2026-04-15T18:00:00+09:00",
            ),
            HumanReviewFeedback(
                item_ref=reviewed_item.review_item_id,
                human_label="drop",
                note="Alias was too broad",
                rule_feedback_tag="alias_noise",
                reviewed_at="2026-04-15T18:05:00+09:00",
                reviewer="operator-a",
                session_tag="batch-1",
            ),
        ]

        rows = build_review_queue_rows(
            review_payload=_review_payload([reviewed_item, unresolved_item]),
            latest_feedback_by_ref=latest_feedback_by_item_ref(feedback_items),
        )

        self.assertEqual(rows[0]["already_reviewed"], "true")
        self.assertEqual(rows[0]["latest_human_label"], "drop")
        self.assertEqual(rows[0]["latest_rule_feedback_tag"], "alias_noise")
        self.assertEqual(rows[0]["latest_note"], "Alias was too broad")
        self.assertEqual(rows[0]["latest_reviewer"], "operator-a")
        self.assertEqual(rows[1]["already_reviewed"], "false")

        unresolved_rows = build_review_queue_rows(
            review_payload=_review_payload([reviewed_item, unresolved_item]),
            latest_feedback_by_ref=latest_feedback_by_item_ref(feedback_items),
            exclude_reviewed=True,
        )

        self.assertEqual(len(unresolved_rows), 1)
        self.assertEqual(unresolved_rows[0]["review_item_id"], unresolved_item.review_item_id)

    def test_build_review_queue_rows_supports_rereview_filters_and_noisy_priority(self) -> None:
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        keyword_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        keep_item = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        feedback = latest_feedback_by_item_ref(
            [
                HumanReviewFeedback(
                    item_ref=alias_item.review_item_id,
                    human_label="drop",
                    rule_feedback_tag="alias_noise",
                    reviewed_at="2026-04-15T18:05:00+09:00",
                    reviewer="operator-a",
                    session_tag="session-1",
                ),
                HumanReviewFeedback(
                    item_ref=keep_item.review_item_id,
                    human_label="keep",
                    reviewed_at="2026-04-15T18:06:00+09:00",
                    reviewer="operator-b",
                    session_tag="session-2",
                ),
            ]
        )
        payload = _review_payload([alias_item, keyword_item, keep_item])
        payload["calibration_summary"] = {
            "noisy_query_sample": ["ETF"],
            "noisy_alias_sample": ["삼전"],
        }

        reviewed_drop_rows = build_review_queue_rows(
            review_payload=payload,
            latest_feedback_by_ref=feedback,
            reviewed_only=True,
            latest_human_label="drop",
            latest_reviewer="operator-a",
            latest_session_tag="session-1",
            latest_rule_feedback_tag="alias_noise",
        )
        noisy_rows = build_review_queue_rows(
            review_payload=payload,
            latest_feedback_by_ref=feedback,
            noisy_query_only=True,
        )

        self.assertEqual([row["review_item_id"] for row in reviewed_drop_rows], [alias_item.review_item_id])
        self.assertEqual(
            [row["query"] for row in noisy_rows],
            ["삼전", "ETF"],
        )

    def test_build_review_queue_rows_uses_human_report_disagreement_presets(self) -> None:
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        payload = _review_payload([alias_item, etf_item])
        report = {
            "per_origin_disagreement_counts": {
                "alias": {
                    "disagreement": 3,
                    "reviewed": 4,
                    "disagreement_rate": 0.75,
                },
                "query_keyword": {
                    "disagreement": 1,
                    "reviewed": 4,
                    "disagreement_rate": 0.25,
                },
            },
            "per_classification_disagreement_counts": {
                "etf": {
                    "disagreement": 2,
                    "reviewed": 3,
                    "disagreement_rate": 0.6667,
                }
            },
            "repeated_query_disagreements": [["ETF", 2]],
        }

        origin_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            disagreement_preset="disagreement_origin",
            min_disagreement_count=2,
            min_disagreement_rate=0.5,
        )
        classification_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            disagreement_preset="disagreement_classification",
            min_disagreement_count=2,
            min_disagreement_rate=0.5,
        )
        query_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            disagreement_preset="repeated_query_disagreement",
            min_query_disagreement_count=2,
        )

        self.assertEqual([row["review_item_id"] for row in origin_rows], [alias_item.review_item_id])
        self.assertEqual(origin_rows[0]["rereview_reason"], "origin_disagreement")
        self.assertEqual(origin_rows[0]["disagreement_scope"], "origin:alias")
        self.assertEqual(
            [row["review_item_id"] for row in classification_rows],
            [etf_item.review_item_id],
        )
        self.assertEqual(classification_rows[0]["rereview_reason"], "classification_disagreement")
        self.assertEqual([row["review_item_id"] for row in query_rows], [etf_item.review_item_id])
        self.assertEqual(query_rows[0]["disagreement_scope"], "query:ETF")

    def test_build_review_queue_rows_combines_disagreement_presets_with_or(self) -> None:
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        report = {
            "per_origin_disagreement_counts": {
                "alias": {
                    "disagreement": 3,
                    "reviewed": 4,
                    "disagreement_rate": 0.75,
                },
            },
            "per_classification_disagreement_counts": {},
            "repeated_query_disagreements": [["ETF", 2]],
        }

        rows = build_review_queue_rows(
            review_payload=_review_payload([alias_item, etf_item]),
            human_review_report=report,
            disagreement_preset=[
                "disagreement_origin",
                "repeated_query_disagreement",
            ],
            min_disagreement_count=2,
            min_disagreement_rate=0.5,
            min_query_disagreement_count=2,
        )

        self.assertEqual(
            [row["review_item_id"] for row in rows],
            [etf_item.review_item_id, alias_item.review_item_id],
        )
        self.assertEqual(rows[0]["rereview_reason"], "repeated_query_disagreement")
        self.assertEqual(rows[0]["priority_score"], "75")
        self.assertEqual(rows[1]["rereview_reason"], "origin_disagreement")
        self.assertEqual(rows[1]["priority_score"], "60")

    def test_build_review_queue_rows_combines_assist_and_error_reasons(self) -> None:
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        feedback = latest_feedback_by_item_ref(
            [
                HumanReviewFeedback(
                    item_ref=alias_item.review_item_id,
                    human_label="drop",
                    reviewed_at="2026-04-15T18:05:00+09:00",
                ),
            ]
        )
        report = {
            "calibration_assist": [
                {
                    "type": "origin_high_disagreement",
                    "origin": "alias",
                    "disagreement": 3,
                    "disagreement_rate": 0.75,
                },
            ],
            "error_counts": {"false_keep": 1},
        }

        rows = build_review_queue_rows(
            review_payload=_review_payload([alias_item]),
            latest_feedback_by_ref=feedback,
            human_review_report=report,
            disagreement_preset="false_keep_focus",
            assist_preset="origin_high_disagreement",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["rereview_reason"],
            "assist_origin_high_disagreement;false_keep_focus",
        )
        self.assertEqual(rows[0]["matched_signals"], "assist_origin_high_disagreement;false_keep_focus")
        self.assertEqual(rows[0]["reason_count"], "2")
        self.assertEqual(rows[0]["priority_score"], "155")
        self.assertEqual(
            rows[0]["disagreement_scope"],
            "origin:alias;error:false_keep",
        )

    def test_build_review_queue_rows_combines_queue_signals_with_disagreement_presets(self) -> None:
        suspicious_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="keep",
            suspicious=True,
        )
        false_drop_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        feedback = latest_feedback_by_item_ref(
            [
                HumanReviewFeedback(
                    item_ref=false_drop_item.review_item_id,
                    human_label="weak_keep",
                    reviewed_at="2026-04-15T18:06:00+09:00",
                ),
            ]
        )

        rows = build_review_queue_rows(
            review_payload=_review_payload([suspicious_item, false_drop_item]),
            latest_feedback_by_ref=feedback,
            human_review_report={"error_counts": {"false_drop": 1}},
            disagreement_preset="false_drop_focus",
            queue_signal="suspicious",
        )

        self.assertEqual(
            [row["review_item_id"] for row in rows],
            [false_drop_item.review_item_id, suspicious_item.review_item_id],
        )
        self.assertEqual(rows[0]["rereview_reason"], "false_drop_focus")
        self.assertEqual(rows[0]["priority_score"], "100")
        self.assertEqual(rows[1]["rereview_reason"], "suspicious_focus")
        self.assertEqual(rows[1]["priority_score"], "40")

    def test_build_review_queue_rows_sorts_by_priority_before_max_items(self) -> None:
        weak_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        suspicious_item = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=True,
        )
        false_drop_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        feedback = latest_feedback_by_item_ref(
            [
                HumanReviewFeedback(
                    item_ref=false_drop_item.review_item_id,
                    human_label="keep",
                    reviewed_at="2026-04-15T18:06:00+09:00",
                ),
            ]
        )

        rows = build_review_queue_rows(
            review_payload=_review_payload([weak_item, suspicious_item, false_drop_item]),
            latest_feedback_by_ref=feedback,
            human_review_report={"error_counts": {"false_drop": 1}},
            disagreement_preset="false_drop_focus",
            queue_signal=["weak_keep", "suspicious"],
            max_items=2,
        )

        self.assertEqual(
            [row["review_item_id"] for row in rows],
            [false_drop_item.review_item_id, suspicious_item.review_item_id],
        )
        self.assertEqual([row["priority_score"] for row in rows], ["100", "40"])

    def test_build_review_queue_rows_can_use_calibration_assist_hints(self) -> None:
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        payload = _review_payload([alias_item, etf_item])
        report = {
            "calibration_assist": [
                {
                    "type": "origin_high_disagreement",
                    "origin": "alias",
                    "disagreement": 3,
                    "disagreement_rate": 0.75,
                },
                {
                    "type": "classification_high_disagreement",
                    "classification": "etf",
                    "disagreement": 2,
                    "disagreement_rate": 0.6667,
                },
                {
                    "type": "repeated_query_disagreement",
                    "query": "ETF",
                    "count": 2,
                },
            ]
        }

        origin_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            assist_preset="origin_high_disagreement",
        )
        classification_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            assist_preset="classification_high_disagreement",
        )
        query_rows = build_review_queue_rows(
            review_payload=payload,
            human_review_report=report,
            assist_preset="repeated_query_disagreement",
        )

        self.assertEqual([row["review_item_id"] for row in origin_rows], [alias_item.review_item_id])
        self.assertEqual(origin_rows[0]["rereview_reason"], "assist_origin_high_disagreement")
        self.assertEqual(
            [row["review_item_id"] for row in classification_rows],
            [etf_item.review_item_id],
        )
        self.assertEqual(
            classification_rows[0]["rereview_reason"],
            "assist_classification_high_disagreement",
        )
        self.assertEqual([row["review_item_id"] for row in query_rows], [etf_item.review_item_id])
        self.assertEqual(query_rows[0]["rereview_reason"], "assist_repeated_query_disagreement")

    def test_build_review_queue_rows_supports_false_keep_and_false_drop_focus(self) -> None:
        false_keep_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        false_drop_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        feedback = latest_feedback_by_item_ref(
            [
                HumanReviewFeedback(
                    item_ref=false_keep_item.review_item_id,
                    human_label="drop",
                    reviewed_at="2026-04-15T18:05:00+09:00",
                ),
                HumanReviewFeedback(
                    item_ref=false_drop_item.review_item_id,
                    human_label="weak_keep",
                    reviewed_at="2026-04-15T18:06:00+09:00",
                ),
            ]
        )
        payload = _review_payload([false_keep_item, false_drop_item])

        false_keep_rows = build_review_queue_rows(
            review_payload=payload,
            latest_feedback_by_ref=feedback,
            human_review_report={"error_counts": {"false_keep": 1}},
            disagreement_preset="false_keep_focus",
        )
        false_drop_rows = build_review_queue_rows(
            review_payload=payload,
            latest_feedback_by_ref=feedback,
            human_review_report={"error_counts": {"false_drop": 1}},
            disagreement_preset="false_drop_focus",
        )

        self.assertEqual(
            [row["review_item_id"] for row in false_keep_rows],
            [false_keep_item.review_item_id],
        )
        self.assertEqual(false_keep_rows[0]["rereview_reason"], "false_keep_focus")
        self.assertEqual(
            [row["review_item_id"] for row in false_drop_rows],
            [false_drop_item.review_item_id],
        )
        self.assertEqual(false_drop_rows[0]["rereview_reason"], "false_drop_focus")

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

    def test_export_cli_can_write_csv_with_bom_and_exclude_reviewed(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        reviewed_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        unresolved_item = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([reviewed_item, unresolved_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=reviewed_item.review_item_id,
                human_label="drop",
                reviewed_at="2026-04-15T18:00:00+09:00",
            ),
        )
        csv_path = directory / "queue_bom.csv"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(csv_path),
                    "--format",
                    "csv",
                    "--csv-bom",
                    "--exclude-reviewed",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_item_id"], unresolved_item.review_item_id)

    def test_export_cli_supports_priority_and_latest_feedback_filters(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        reviewed_drop = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        reviewed_keep = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([reviewed_drop, reviewed_keep]), ensure_ascii=False),
            encoding="utf-8",
        )
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=reviewed_drop.review_item_id,
                human_label="drop",
                rule_feedback_tag="alias_noise",
                reviewed_at="2026-04-15T18:00:00+09:00",
                reviewer="operator-a",
                session_tag="session-1",
            ),
        )
        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=reviewed_keep.review_item_id,
                human_label="keep",
                reviewed_at="2026-04-15T18:01:00+09:00",
                reviewer="operator-b",
                session_tag="session-2",
            ),
        )
        output_path = directory / "rereview.csv"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--reviewed-only",
                    "--latest-human-label",
                    "drop",
                    "--latest-reviewer",
                    "operator-a",
                    "--latest-session-tag",
                    "session-1",
                    "--latest-rule-feedback-tag",
                    "alias_noise",
                ]
            )

        self.assertEqual(exit_code, 0)
        with output_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_item_id"], reviewed_drop.review_item_id)

    def test_export_cli_supports_disagreement_report_preset(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        other_item = _review_item(
            symbol="000660",
            query="SK하이닉스",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([alias_item, other_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        report_path = directory / "latest_naver_news_human_review_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "per_origin_disagreement_counts": {
                        "alias": {
                            "disagreement": 2,
                            "reviewed": 3,
                            "disagreement_rate": 0.6667,
                        }
                    },
                    "per_classification_disagreement_counts": {},
                    "repeated_query_disagreements": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        output_path = directory / "disagreement_origin.csv"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--disagreement-preset",
                    "disagreement_origin",
                    "--min-disagreement-count",
                    "2",
                    "--min-disagreement-rate",
                    "0.5",
                ]
            )

        self.assertEqual(exit_code, 0)
        with output_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_item_id"], alias_item.review_item_id)
        self.assertEqual(rows[0]["rereview_reason"], "origin_disagreement")

    def test_export_cli_supports_assist_preset(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=False,
        )
        stock_item = _review_item(
            symbol="005930",
            query="삼성전자",
            query_origin="korean_name",
            classification="stock",
            decision="keep",
            suspicious=False,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([etf_item, stock_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "latest_naver_news_human_review_report.json").write_text(
            json.dumps(
                {
                    "calibration_assist": [
                        {
                            "type": "classification_high_disagreement",
                            "classification": "etf",
                            "disagreement": 2,
                            "disagreement_rate": 0.6667,
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        output_path = directory / "assist.csv"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--assist-preset",
                    "classification_high_disagreement",
                ]
            )

        self.assertEqual(exit_code, 0)
        with output_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_item_id"], etf_item.review_item_id)
        self.assertEqual(rows[0]["rereview_reason"], "assist_classification_high_disagreement")

    def test_export_cli_supports_repeated_and_comma_separated_multi_signal_presets(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=True,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([alias_item, etf_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "latest_naver_news_human_review_report.json").write_text(
            json.dumps(
                {
                    "per_origin_disagreement_counts": {
                        "alias": {
                            "disagreement": 2,
                            "reviewed": 3,
                            "disagreement_rate": 0.6667,
                        }
                    },
                    "per_classification_disagreement_counts": {},
                    "repeated_query_disagreements": [["ETF", 2]],
                    "calibration_assist": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        output_path = directory / "multi_signal.csv"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--disagreement-preset",
                    "disagreement_origin",
                    "--disagreement-preset",
                    "repeated_query_disagreement",
                    "--queue-signal",
                    "suspicious,noisy",
                    "--min-disagreement-count",
                    "2",
                    "--min-disagreement-rate",
                    "0.5",
                    "--min-query-disagreement-count",
                    "2",
                ]
            )

        self.assertEqual(exit_code, 0)
        with output_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(
            [row["review_item_id"] for row in rows],
            [etf_item.review_item_id, alias_item.review_item_id],
        )
        self.assertEqual(rows[1]["rereview_reason"], "origin_disagreement")
        self.assertEqual(rows[1]["priority_score"], "60")
        self.assertEqual(
            rows[0]["rereview_reason"],
            "suspicious_focus;repeated_query_disagreement",
        )
        self.assertEqual(rows[0]["matched_signals"], "suspicious_focus;repeated_query_disagreement")
        self.assertEqual(rows[0]["reason_count"], "2")
        self.assertEqual(rows[0]["priority_score"], "115")

    def test_export_cli_can_write_queue_summary_manifest(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=True,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([alias_item, etf_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "latest_naver_news_human_review_report.json").write_text(
            json.dumps(
                {
                    "per_origin_disagreement_counts": {
                        "alias": {
                            "disagreement": 2,
                            "reviewed": 3,
                            "disagreement_rate": 0.6667,
                        }
                    },
                    "per_classification_disagreement_counts": {},
                    "repeated_query_disagreements": [["ETF", 2]],
                    "calibration_assist": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=alias_item.review_item_id,
                human_label="drop",
                reviewed_at="2026-04-15T18:00:00+09:00",
            ),
        )
        output_path = directory / "priority_queue.csv"
        summary_path = directory / "priority_queue_summary.json"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--disagreement-preset",
                    "disagreement_origin,repeated_query_disagreement",
                    "--queue-signal",
                    "suspicious",
                    "--min-disagreement-count",
                    "2",
                    "--min-disagreement-rate",
                    "0.5",
                    "--summary-output",
                    str(summary_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["provider"], "naver_news")
        self.assertEqual(summary["output_path"], str(output_path))
        self.assertEqual(
            summary["human_review_report_path"],
            str(directory / "latest_naver_news_human_review_report.json"),
        )
        self.assertEqual(
            summary["applied_disagreement_presets"],
            ["disagreement_origin", "repeated_query_disagreement"],
        )
        self.assertEqual(summary["applied_queue_signals"], ["suspicious"])
        self.assertEqual(summary["applied_filters"]["min_disagreement_count"], 2)
        self.assertEqual(summary["selected_count"], 2)
        self.assertEqual(summary["reviewed_count"], 1)
        self.assertEqual(summary["unreviewed_count"], 1)
        self.assertEqual(summary["matched_signal_counts"]["origin_disagreement"], 1)
        self.assertEqual(summary["matched_signal_counts"]["suspicious_focus"], 1)
        self.assertEqual(summary["priority_score_buckets"]["100_plus"], 1)
        self.assertEqual(summary["top_priority_row_samples"][0]["priority_score"], "115")
        self.assertEqual(
            summary["top_matched_signals"][0],
            {"value": "origin_disagreement", "count": 1},
        )

    def test_export_cli_can_write_queue_summary_comparison(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        alias_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        etf_item = _review_item(
            symbol="069500",
            query="ETF",
            query_origin="query_keyword",
            classification="etf",
            decision="drop",
            suspicious=True,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([alias_item, etf_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "latest_naver_news_human_review_report.json").write_text(
            json.dumps(
                {
                    "per_origin_disagreement_counts": {
                        "alias": {
                            "disagreement": 2,
                            "reviewed": 3,
                            "disagreement_rate": 0.6667,
                        }
                    },
                    "per_classification_disagreement_counts": {},
                    "repeated_query_disagreements": [["ETF", 2]],
                    "calibration_assist": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        repository.append_feedback_sync(
            provider="naver_news",
            feedback=HumanReviewFeedback(
                item_ref=alias_item.review_item_id,
                human_label="drop",
                reviewed_at="2026-04-15T18:00:00+09:00",
            ),
        )
        previous_summary_path = directory / "previous_queue_summary.json"
        previous_summary_path.write_text(
            json.dumps(
                {
                    "generated_at": "2026-04-15T18:00:00+09:00",
                    "provider": "naver_news",
                    "output_path": "old_queue.csv",
                    "output_format": "csv",
                    "selected_count": 1,
                    "reviewed_count": 0,
                    "unreviewed_count": 1,
                    "matched_signal_counts": {"origin_disagreement": 1},
                    "rereview_reason_counts": {"origin_disagreement": 1},
                    "priority_score_buckets": {
                        "0": 0,
                        "1_39": 0,
                        "40_59": 0,
                        "60_99": 1,
                        "100_plus": 0,
                    },
                    "top_matched_signals": [{"value": "origin_disagreement", "count": 1}],
                    "applied_disagreement_presets": ["disagreement_origin"],
                    "applied_assist_presets": [],
                    "applied_queue_signals": [],
                    "applied_filters": {
                        "min_disagreement_count": 1,
                        "latest_human_label": "",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        output_path = directory / "priority_queue.csv"
        summary_path = directory / "priority_queue_summary.json"
        comparison_path = directory / "priority_queue_comparison.json"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(output_path),
                    "--format",
                    "csv",
                    "--disagreement-preset",
                    "disagreement_origin,repeated_query_disagreement",
                    "--queue-signal",
                    "suspicious",
                    "--min-disagreement-count",
                    "2",
                    "--min-disagreement-rate",
                    "0.5",
                    "--summary-output",
                    str(summary_path),
                    "--compare-summary-path",
                    str(previous_summary_path),
                    "--comparison-output",
                    str(comparison_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        self.assertTrue(comparison["comparison_available"])
        self.assertEqual(comparison["previous_summary_path"], str(previous_summary_path))
        self.assertEqual(comparison["count_deltas"]["selected_count"]["delta"], 1)
        self.assertEqual(comparison["count_deltas"]["reviewed_count"]["delta"], 1)
        self.assertEqual(
            comparison["matched_signal_count_deltas"]["origin_disagreement"]["delta"],
            0,
        )
        self.assertEqual(
            comparison["matched_signal_count_deltas"]["repeated_query_disagreement"]["current"],
            1,
        )
        self.assertEqual(
            comparison["priority_score_bucket_deltas"]["100_plus"]["delta"],
            1,
        )
        self.assertEqual(
            comparison["metadata_comparison"]["applied_queue_signals"]["added"],
            ["suspicious"],
        )
        self.assertEqual(
            comparison["metadata_comparison"]["filter_differences"]["min_disagreement_count"],
            {"current": 2, "previous": 1},
        )
        hint_types = {hint["type"] for hint in comparison["interpretation_hints"]}
        self.assertIn("noise_or_suspicious_focus_increased", hint_types)
        self.assertIn("repeated_query_disagreement_emphasis_increased", hint_types)
        self.assertIn("queue_became_more_reviewed_heavy", hint_types)
        self.assertIn("filters_changed", hint_types)
        self.assertIn(
            "Review noisy/suspicious rows separately from relevance recovery rows.",
            comparison["strategy_notes"],
        )
        self.assertIn(
            "Inspect repeated query terms before changing broad origin or classification thresholds.",
            comparison["strategy_notes"],
        )

    def test_export_cli_queue_summary_comparison_handles_missing_previous(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        review_item = _review_item(
            symbol="005930",
            query="삼전",
            query_origin="alias",
            classification="stock",
            decision="weak_keep",
            suspicious=False,
        )
        (directory / "latest_naver_news_review.json").write_text(
            json.dumps(_review_payload([review_item]), ensure_ascii=False),
            encoding="utf-8",
        )
        comparison_path = directory / "first_run_comparison.json"

        with redirect_stdout(io.StringIO()):
            exit_code = export_main(
                [
                    "--directory",
                    str(directory),
                    "--output",
                    str(directory / "queue.csv"),
                    "--format",
                    "csv",
                    "--comparison-output",
                    str(comparison_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        self.assertFalse(comparison["comparison_available"])
        self.assertEqual(comparison["unavailable_reason"], "previous_summary_not_found")
        self.assertEqual(comparison["current_selected_count"], 1)

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

    def test_import_feedback_rows_dry_run_does_not_write(self) -> None:
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
                }
            ],
            reviewed_at="2026-04-15T18:00:00+09:00",
            dry_run=True,
        )

        self.assertEqual(result["imported_count"], 1)
        self.assertTrue(result["dry_run"])
        self.assertEqual(repository.list_feedback_sync(provider="naver_news"), [])

    def test_import_cli_reads_labeled_csv(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        input_path = directory / "labeled.csv"
        with input_path.open("w", encoding="utf-8-sig", newline="") as file:
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

    def test_import_cli_dry_run_reads_bom_csv_without_writing(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        input_path = directory / "labeled_bom.csv"
        with input_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["review_item_id", "human_label"])
            writer.writeheader()
            writer.writerow({"review_item_id": "item-1", "human_label": "drop"})
            writer.writerow({"review_item_id": "item-2", "human_label": "bad_label"})

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
                    "--dry-run",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("dry_run imported=1 skipped=0 invalid=1", output.getvalue())
        repository = JsonlDiscoveryHumanReviewRepository(directory=directory)
        self.assertEqual(repository.list_feedback_sync(provider="naver_news"), [])

    def test_import_cli_dry_run_can_write_summary_artifact(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        directory = Path(temp_dir.name)
        input_path = directory / "labeled.csv"
        summary_path = directory / "dry_run_summary.json"
        with input_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["review_item_id", "human_label"])
            writer.writeheader()
            writer.writerow({"review_item_id": "item-1", "human_label": "drop"})
            writer.writerow({"review_item_id": "item-2", "human_label": ""})

        with redirect_stdout(io.StringIO()):
            exit_code = import_main(
                [
                    "--directory",
                    str(directory),
                    "--input",
                    str(input_path),
                    "--format",
                    "csv",
                    "--dry-run",
                    "--summary-output",
                    str(summary_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["imported_count"], 1)
        self.assertEqual(summary["skipped_count"], 1)


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
