from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord
from src.ingestion.discovery.evaluation import DiscoveryDecision, evaluate_discovery_item
from src.ingestion.discovery.filtering import (
    DiscoveryCandidate,
    filter_discovery_candidates,
)


class DiscoveryQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.as_of = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        self.record = SymbolRecord(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            korean_name="삼성전자",
            normalized_name="삼성전자",
            aliases=["삼전"],
        )

    def test_evaluation_keeps_strong_symbol_match(self) -> None:
        evaluation = evaluate_discovery_item(
            item=_raw_item(
                title="삼성전자 AI 반도체 투자 확대",
                body="삼성전자가 신규 반도체 투자를 발표했다.",
                as_of=self.as_of,
            ),
            record=self.record,
            query="삼성전자",
            as_of=self.as_of,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.KEEP)
        self.assertIn("strong_symbol_or_query_match", evaluation.reasons)

    def test_evaluation_drops_generic_noise_without_symbol_match(self) -> None:
        evaluation = evaluate_discovery_item(
            item=_raw_item(
                title="특징주 급등 마감",
                body="코스피 주요 종목이 상승했다.",
                as_of=self.as_of,
            ),
            record=self.record,
            query="삼성전자",
            as_of=self.as_of,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.DROP)
        self.assertTrue(evaluation.suspicious)

    def test_filtering_tracks_duplicates_and_quality_metrics(self) -> None:
        candidates = [
            DiscoveryCandidate(
                item=_raw_item(
                    title="삼성전자 AI 반도체 투자 확대",
                    body="삼성전자 신규 투자 뉴스",
                    as_of=self.as_of,
                    url="https://example.com/a",
                ),
                record=self.record,
                query="삼성전자",
                query_origin="korean_name",
                dedup_key="https://example.com/a",
            ),
            DiscoveryCandidate(
                item=_raw_item(
                    title="삼성전자 AI 반도체 투자 확대",
                    body="같은 기사",
                    as_of=self.as_of,
                    url="https://example.com/a",
                ),
                record=self.record,
                query="삼성전자",
                query_origin="korean_name",
                dedup_key="https://example.com/a",
            ),
            DiscoveryCandidate(
                item=_raw_item(
                    title="특징주 급등 마감",
                    body="코스피 주요 종목이 상승했다.",
                    as_of=self.as_of,
                    url="https://example.com/noise",
                ),
                record=self.record,
                query="삼성전자",
                query_origin="korean_name",
                dedup_key="https://example.com/noise",
            ),
        ]

        result = filter_discovery_candidates(candidates=candidates, as_of=self.as_of)

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.metrics.raw_discovered_item_count, 3)
        self.assertEqual(result.metrics.deduplicated_item_count, 2)
        self.assertEqual(result.metrics.kept_item_count, 1)
        self.assertEqual(result.metrics.dropped_item_count, 1)
        self.assertEqual(result.metrics.suspicious_item_count, 1)
        self.assertEqual(result.items[0].metadata["discovery_decision"], "keep")

    def test_implausible_publish_time_is_weak_keep_for_otherwise_relevant_item(self) -> None:
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
            as_of=self.as_of,
        )

        self.assertEqual(evaluation.decision, DiscoveryDecision.WEAK_KEEP)
        self.assertIn("publish_time_suspicious", evaluation.reasons)


def _raw_item(
    *,
    title: str,
    body: str,
    as_of: datetime,
    url: str = "https://example.com/news",
    published_at: datetime | None = None,
) -> RawNewsItem:
    return RawNewsItem(
        id="raw_test",
        source="naver_news",
        source_id=f"test:{url}",
        title=title,
        body=body,
        url=url,
        published_at=published_at or as_of,
        collected_at=as_of,
        language="ko",
        symbols=["005930"],
        metadata={"provider_payload": "{}"},
    )


if __name__ == "__main__":
    unittest.main()
