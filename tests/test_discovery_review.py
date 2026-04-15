from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord
from src.db.repositories.discovery_review_repository import JsonDiscoveryReviewRepository
from src.ingestion.discovery.calibration import build_calibration_summary
from src.ingestion.discovery.filtering import DiscoveryCandidate, filter_discovery_candidates


class DiscoveryReviewTest(unittest.TestCase):
    def test_review_items_include_query_origin_and_classification(self) -> None:
        as_of = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        record = SymbolRecord(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            korean_name="삼성전자",
            metadata={"classification": "stock"},
        )

        result = filter_discovery_candidates(
            candidates=[
                DiscoveryCandidate(
                    item=_raw_item(
                        title="삼성전자 반도체 투자",
                        body="삼성전자 반도체 투자가 확대됐다.",
                        as_of=as_of,
                    ),
                    record=record,
                    query="삼성전자 반도체",
                    query_origin="query_keyword",
                    dedup_key="https://example.com/a",
                )
            ],
            as_of=as_of,
        )

        self.assertEqual(result.review_items[0].query_origin, "query_keyword")
        self.assertEqual(result.review_items[0].classification, "stock")
        self.assertEqual(result.review_items[0].discovery_decision, "keep")

    def test_calibration_summary_groups_decisions(self) -> None:
        as_of = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        record = SymbolRecord(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            korean_name="삼성전자",
            metadata={"classification": "stock"},
        )

        result = filter_discovery_candidates(
            candidates=[
                DiscoveryCandidate(
                    item=_raw_item(
                        title="삼성전자 반도체 투자",
                        body="삼성전자 반도체 투자가 확대됐다.",
                        as_of=as_of,
                        url="https://example.com/keep",
                    ),
                    record=record,
                    query="삼성전자",
                    query_origin="korean_name",
                    dedup_key="https://example.com/keep",
                ),
                DiscoveryCandidate(
                    item=_raw_item(
                        title="특징주 급등 마감",
                        body="코스피 주요 종목이 상승했다.",
                        as_of=as_of,
                        url="https://example.com/drop",
                    ),
                    record=record,
                    query="삼전",
                    query_origin="alias",
                    dedup_key="https://example.com/drop",
                ),
            ],
            as_of=as_of,
        )
        summary = build_calibration_summary(result.review_items)

        self.assertEqual(summary.per_query["삼성전자"].keep, 1)
        self.assertEqual(summary.per_query["삼전"].drop, 1)
        self.assertEqual(summary.per_symbol["005930"].keep, 1)
        self.assertEqual(summary.per_symbol["005930"].drop, 1)
        self.assertEqual(summary.per_classification["stock"].keep, 1)
        self.assertEqual(summary.noisy_alias_sample, ["삼전"])
        self.assertEqual(summary.ambiguous_symbol_sample, ["005930"])

    def test_repository_writes_latest_review_artifact(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        generated_at = datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        repository = JsonDiscoveryReviewRepository(directory=Path(temp_dir.name))

        repository.save_review_sync(
            provider="naver_news",
            generated_at=generated_at,
            review_items=[],
            calibration_summary=build_calibration_summary([]),
        )

        latest_path = Path(temp_dir.name) / "latest_naver_news_review.json"
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["provider"], "naver_news")
        self.assertEqual(payload["items"], [])
        self.assertIn("calibration_summary", payload)


def _raw_item(
    *,
    title: str,
    body: str,
    as_of: datetime,
    url: str = "https://example.com/a",
) -> RawNewsItem:
    return RawNewsItem(
        id="raw_test",
        source="naver_news",
        source_id=f"test:{url}",
        title=title,
        body=body,
        url=url,
        published_at=as_of,
        collected_at=as_of,
        language="ko",
        symbols=["005930"],
        metadata={"provider_payload": "{}"},
    )


if __name__ == "__main__":
    unittest.main()
