from __future__ import annotations

import unittest
from datetime import datetime

from src.contracts.symbols import SymbolRecord
from src.ingestion.clients.http import ProviderClientError
from src.ingestion.clients.naver_news_client import NaverNewsClient
from src.ingestion.loaders.naver_news_loader import NaverNewsDiscoverySource
from src.ingestion.loaders.query_strategy import build_symbol_news_queries


class FakeNaverNewsClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search_news(self, *, query: str, display: int, start: int = 1, sort: str = "date"):
        self.queries.append(query)
        return {
            "items": [
                {
                    "title": "<b>삼성전자</b> AI 반도체 투자",
                    "description": "삼성전자 신규 투자 뉴스",
                    "originallink": "https://example.com/news/1",
                    "link": "https://news.naver.com/1",
                    "pubDate": "Wed, 15 Apr 2026 10:10:00 +0900",
                },
                {
                    "title": "중복 기사",
                    "description": "중복",
                    "originallink": "https://example.com/news/1",
                    "link": "https://news.naver.com/dup",
                    "pubDate": "Wed, 15 Apr 2026 10:11:00 +0900",
                },
            ]
        }


class FailingNaverNewsClient:
    def search_news(self, *, query: str, display: int, start: int = 1, sort: str = "date"):
        if "fail" in query:
            raise RuntimeError("naver failure")
        return {"items": []}


class UnusedHttpClient:
    def get_json(self, *args, **kwargs):
        raise AssertionError("HTTP should not be called without credentials")


class NaverNewsLoaderTest(unittest.IsolatedAsyncioTestCase):
    def test_naver_news_client_requires_credentials(self) -> None:
        client = NaverNewsClient(
            base_url="https://openapi.naver.com",
            client_id="",
            client_secret="",
            http=UnusedHttpClient(),
        )

        with self.assertRaises(ProviderClientError):
            client.search_news(query="삼성전자", display=1)

    def test_query_strategy_uses_primary_fields_and_caps_queries(self) -> None:
        record = SymbolRecord(
            symbol="005930",
            name="삼성전자",
            market="KOSPI",
            korean_name="삼성전자",
            normalized_name="삼성전자",
            aliases=["삼성전자", "삼전"],
            query_keywords=["삼성전자", "삼성전자 반도체"],
        )

        queries = build_symbol_news_queries(
            record,
            include_aliases=True,
            include_query_keywords=True,
            limit=3,
        )

        self.assertEqual(queries, ["삼성전자", "삼전", "삼성전자 반도체"])

    async def test_naver_news_loader_maps_results_to_raw_news_items(self) -> None:
        client = FakeNaverNewsClient()
        source = NaverNewsDiscoverySource(
            client=client,
            symbol_records=[
                SymbolRecord(
                    symbol="005930",
                    name="삼성전자",
                    market="KOSPI",
                    korean_name="삼성전자",
                    normalized_name="삼성전자",
                )
            ],
            query_limit_per_symbol=1,
            result_limit_per_query=5,
            include_aliases=False,
            include_query_keywords=False,
        )

        items = await source.fetch_daily(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "naver_news")
        self.assertEqual(items[0].symbols, ["005930"])
        self.assertEqual(items[0].title, "삼성전자 AI 반도체 투자")
        self.assertEqual(source.last_execution_report.query_count, 1)
        self.assertEqual(source.last_execution_report.item_count, 1)
        self.assertEqual(source.last_execution_report.raw_discovered_item_count, 2)
        self.assertEqual(source.last_execution_report.deduplicated_item_count, 1)
        self.assertEqual(source.last_execution_report.kept_item_count, 1)
        self.assertEqual(items[0].metadata["discovery_decision"], "keep")

    async def test_naver_news_loader_reports_failed_queries(self) -> None:
        source = NaverNewsDiscoverySource(
            client=FailingNaverNewsClient(),
            symbol_records=[
                SymbolRecord(
                    symbol="000001",
                    name="fail",
                    market="KOSPI",
                    korean_name="fail",
                ),
                SymbolRecord(
                    symbol="000002",
                    name="ok",
                    market="KOSPI",
                    korean_name="ok",
                ),
            ],
            query_limit_per_symbol=1,
            result_limit_per_query=5,
            include_aliases=False,
            include_query_keywords=False,
        )

        items = await source.fetch_daily(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual(items, [])
        self.assertEqual(source.last_execution_report.query_count, 2)
        self.assertEqual(source.last_execution_report.failed_query_count, 1)
        self.assertTrue(source.last_execution_report.partial_success)
        self.assertEqual(source.last_execution_report.raw_discovered_item_count, 0)


if __name__ == "__main__":
    unittest.main()
