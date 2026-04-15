from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.db.repositories.discovery_review_repository import JsonDiscoveryReviewRepository
from src.ingestion.discovery.calibration import build_calibration_summary
from src.ingestion.discovery.experiment import (
    build_experiment_metadata,
    fingerprint_rule_config,
)
from src.ingestion.discovery.review import DiscoveryReviewItem
from src.ingestion.discovery.rules import discovery_rule_config_from_dict


class DiscoveryExperimentsTest(unittest.TestCase):
    def test_rule_config_fingerprint_is_stable_for_effective_config(self) -> None:
        first = discovery_rule_config_from_dict(
            {
                "generic_noise_terms": ["특징주", "급등"],
                "origin_rules": {"alias": {"score_adjustment": -0.2}},
            }
        )
        second = discovery_rule_config_from_dict(
            {
                "origin_rules": {"alias": {"score_adjustment": -0.2}},
                "generic_noise_terms": ["급등", "특징주"],
            }
        )

        self.assertEqual(fingerprint_rule_config(first), fingerprint_rule_config(second))

    def test_repository_writes_experiment_metadata_and_unavailable_comparison(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        generated_at = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        rules = discovery_rule_config_from_dict({"keep_threshold": 0.75})
        repository = JsonDiscoveryReviewRepository(directory=Path(temp_dir.name))
        review_items = [
            _review_item(
                query="삼성전자",
                query_origin="korean_name",
                decision="keep",
                classification="stock",
            )
        ]

        repository.save_review_sync(
            provider="naver_news",
            generated_at=generated_at,
            review_items=review_items,
            calibration_summary=build_calibration_summary(review_items),
            experiment_metadata=build_experiment_metadata(
                generated_at=generated_at,
                provider="naver_news",
                rules=rules,
                rule_config_path="config/discovery_rules.example.json",
                active_source_symbol_policy="catalog_filtered",
                selected_symbol_count=10,
                query_count=12,
            ),
        )

        review_payload = _read_json(Path(temp_dir.name) / "latest_naver_news_review.json")
        metadata = review_payload["experiment_metadata"]
        self.assertEqual(metadata["rule_config_path"], "config/discovery_rules.example.json")
        self.assertEqual(metadata["active_source_symbol_policy"], "catalog_filtered")
        self.assertEqual(metadata["selected_symbol_count"], 10)
        self.assertEqual(metadata["query_count"], 12)
        self.assertEqual(metadata["rule_config_fingerprint"], fingerprint_rule_config(rules))

        comparison_payload = _read_json(
            Path(temp_dir.name) / "latest_naver_news_calibration_compare.json"
        )
        self.assertFalse(comparison_payload["available"])
        self.assertEqual(comparison_payload["reason"], "previous_review_not_found")

    def test_repository_compares_latest_previous_review_with_current_run(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repository = JsonDiscoveryReviewRepository(directory=Path(temp_dir.name))
        first_at = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        second_at = datetime.fromisoformat("2026-04-15T17:10:00+09:00")
        rules = discovery_rule_config_from_dict({"keep_threshold": 0.8})
        first_items = [
            _review_item(
                query="삼성전자",
                query_origin="korean_name",
                decision="keep",
                classification="stock",
            ),
            _review_item(
                query="삼전",
                query_origin="alias",
                decision="weak_keep",
                classification="stock",
            ),
        ]
        second_items = [
            _review_item(
                query="삼성전자",
                query_origin="korean_name",
                decision="keep",
                classification="stock",
            ),
            _review_item(
                query="삼전",
                query_origin="alias",
                decision="drop",
                classification="stock",
                suspicious=True,
            ),
            _review_item(
                query="ETF",
                query_origin="query_keyword",
                decision="drop",
                classification="etf",
            ),
        ]

        repository.save_review_sync(
            provider="naver_news",
            generated_at=first_at,
            review_items=first_items,
            calibration_summary=build_calibration_summary(first_items),
            experiment_metadata=build_experiment_metadata(
                generated_at=first_at,
                provider="naver_news",
                rules=rules,
                active_source_symbol_policy="catalog_filtered",
                selected_symbol_count=2,
                query_count=2,
            ),
        )
        repository.save_review_sync(
            provider="naver_news",
            generated_at=second_at,
            review_items=second_items,
            calibration_summary=build_calibration_summary(second_items),
            experiment_metadata=build_experiment_metadata(
                generated_at=second_at,
                provider="naver_news",
                rules=rules,
                active_source_symbol_policy="catalog_filtered",
                selected_symbol_count=2,
                query_count=3,
            ),
        )

        comparison_payload = _read_json(
            Path(temp_dir.name) / "latest_naver_news_calibration_compare.json"
        )
        self.assertTrue(comparison_payload["available"])
        self.assertEqual(comparison_payload["decision_counts"]["delta"]["keep"], 0)
        self.assertEqual(comparison_payload["decision_counts"]["delta"]["weak_keep"], -1)
        self.assertEqual(comparison_payload["decision_counts"]["delta"]["drop"], 2)
        self.assertEqual(comparison_payload["suspicious_count"]["delta"], 1)
        self.assertEqual(
            comparison_payload["per_origin_counts"]["alias"]["delta"],
            {"keep": 0, "weak_keep": -1, "drop": 1},
        )
        self.assertEqual(
            comparison_payload["per_classification_counts"]["etf"]["delta"],
            {"keep": 0, "weak_keep": 0, "drop": 1},
        )
        self.assertEqual(comparison_payload["noisy_query_sample_changes"]["added"], ["삼전", "ETF"])


def _review_item(
    *,
    query: str,
    query_origin: str,
    decision: str,
    classification: str,
    suspicious: bool = False,
) -> DiscoveryReviewItem:
    return DiscoveryReviewItem(
        symbol="005930",
        query=query,
        query_origin=query_origin,
        title=query,
        url=f"https://example.com/{query}",
        published_at="2026-04-15T16:10:00+09:00",
        discovery_decision=decision,
        discovery_score=0.8,
        discovery_reasons=[],
        discovery_suspicious=suspicious,
        classification=classification,
    )


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
