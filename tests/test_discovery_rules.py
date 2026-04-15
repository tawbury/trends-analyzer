from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord
from src.ingestion.discovery.evaluation import DiscoveryDecision, evaluate_discovery_item
from src.ingestion.discovery.rules import (
    DiscoveryRuleConfig,
    discovery_rule_config_from_dict,
    load_discovery_rule_config,
)


class DiscoveryRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.as_of = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        self.record = SymbolRecord(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            korean_name="삼성전자",
            metadata={"classification": "stock"},
        )

    def test_rule_config_loads_origin_and_classification_overrides(self) -> None:
        config = discovery_rule_config_from_dict(
            {
                "generic_noise_terms": ["특징주"],
                "keep_threshold": 0.7,
                "origin_rules": {
                    "alias": {
                        "score_adjustment": -0.2,
                        "min_query_length": 3,
                    }
                },
                "classification_rules": {
                    "etf": {
                        "keep_threshold": 0.8,
                        "weak_keep_threshold": 0.5,
                        "score_adjustment": -0.1,
                    }
                },
            }
        )

        self.assertEqual(config.generic_noise_terms, {"특징주"})
        self.assertEqual(config.keep_threshold, 0.7)
        self.assertEqual(config.origin_rule_for("alias").score_adjustment, -0.2)
        self.assertEqual(config.origin_rule_for("alias").min_query_length, 3)
        self.assertEqual(config.thresholds_for("etf"), (0.8, 0.5))
        self.assertEqual(config.classification_score_adjustment("etf"), -0.1)

    def test_origin_penalty_can_downgrade_alias_result(self) -> None:
        rules = discovery_rule_config_from_dict(
            {
                "origin_rules": {
                    "alias": {
                        "score_adjustment": -0.5,
                    }
                }
            }
        )

        evaluation = evaluate_discovery_item(
            item=_raw_item(
                title="삼성전자 반도체 투자",
                body="삼성전자 반도체 투자가 확대됐다.",
                as_of=self.as_of,
            ),
            record=self.record,
            query="삼전",
            query_origin="alias",
            as_of=self.as_of,
            rules=rules,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.WEAK_KEEP)
        self.assertIn("origin_alias_score_adjustment", evaluation.reasons)

    def test_classification_threshold_can_downgrade_result(self) -> None:
        rules = discovery_rule_config_from_dict(
            {
                "classification_rules": {
                    "etf": {
                        "keep_threshold": 0.9,
                        "score_adjustment": -0.25,
                    }
                }
            }
        )
        record = SymbolRecord(
            symbol="123456",
            name="테스트ETF",
            market="KOSPI",
            korean_name="테스트ETF",
            metadata={"classification": "etf"},
        )

        evaluation = evaluate_discovery_item(
            item=_raw_item(
                title="테스트ETF 신규 편입",
                body="테스트ETF 관련 공시가 나왔다.",
                as_of=self.as_of,
            ),
            record=record,
            query="테스트ETF",
            query_origin="korean_name",
            as_of=self.as_of,
            rules=rules,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.WEAK_KEEP)

    def test_publish_window_is_configurable(self) -> None:
        rules = DiscoveryRuleConfig(publish_past_window_days=90)
        item = _raw_item(
            title="삼성전자 신규 투자",
            body="삼성전자 반도체 투자가 확대됐다.",
            as_of=self.as_of,
            published_at=self.as_of - timedelta(days=60),
        )

        evaluation = evaluate_discovery_item(
            item=item,
            record=self.record,
            query="삼성전자",
            query_origin="korean_name",
            as_of=self.as_of,
            rules=rules,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.KEEP)

    def test_load_rule_config_from_json_file(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "rules.json"
        path.write_text(
            json.dumps({"keep_threshold": 0.75}, ensure_ascii=False),
            encoding="utf-8",
        )

        config = load_discovery_rule_config(str(path))

        self.assertEqual(config.keep_threshold, 0.75)


def _raw_item(
    *,
    title: str,
    body: str,
    as_of: datetime,
    published_at: datetime | None = None,
) -> RawNewsItem:
    return RawNewsItem(
        id="raw_test",
        source="naver_news",
        source_id="test",
        title=title,
        body=body,
        url="https://example.com/news",
        published_at=published_at or as_of,
        collected_at=as_of,
        language="ko",
        symbols=["005930"],
        metadata={"provider_payload": "{}"},
    )


if __name__ == "__main__":
    unittest.main()
