from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any

from src.contracts.runtime import CorrelationContext
from src.ingestion.loaders.kis_loader import KisMarketDataSource
from src.ingestion.loaders.kiwoom_loader import KiwoomStockInfoSource


class FakeKisClient:
    def get_invest_opinion(
        self,
        *,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        return {
            "rt_cd": "0",
            "output": [
                {
                    "stck_bsop_date": "20260408",
                    "invt_opnn": "BUY",
                    "mbcr_name": "Example Securities",
                    "hts_goal_prc": "350000",
                    "stck_prdy_clpr": "196500",
                    "dprt": "-41.00",
                }
            ],
        }

    def get_domestic_quote(self, symbol: str) -> dict[str, Any]:
        return {
            "output": {
                "hts_kor_isnm": "Samsung Electronics",
                "stck_prpr": "72000",
                "prdy_ctrt": "1.25",
                "acml_vol": "1234567",
            }
        }


class FakeKiwoomClient:
    def get_stock_info(self, symbol: str) -> dict[str, Any]:
        return {
            "stk_nm": "SK Hynix",
            "cur_prc": "+180000",
            "flu_rt": "2.10",
            "trde_qty": "7654321",
        }


class PartiallyFailingKiwoomClient:
    def get_stock_info(self, symbol: str) -> dict[str, Any]:
        if symbol == "000000":
            raise RuntimeError("bad symbol")
        return FakeKiwoomClient().get_stock_info(symbol)


class SourceLoaderMappingTest(unittest.IsolatedAsyncioTestCase):
    async def test_kis_loader_maps_invest_opinion_to_raw_news_item(self) -> None:
        source = KisMarketDataSource(
            client=FakeKisClient(),
            symbols=["005930"],
            invest_opinion_lookback_days=180,
            invest_opinion_limit_per_symbol=5,
        )
        items = await source.fetch_daily(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "kis")
        self.assertEqual(items[0].symbols, ["005930"])
        self.assertIn("investment_opinion_as_raw_item", items[0].metadata["mapping_type"])
        self.assertIn("BUY", items[0].title)
        self.assertEqual(source.last_execution_report.requested_symbol_count, 1)
        self.assertEqual(source.last_execution_report.succeeded_symbol_count, 1)

    async def test_kiwoom_loader_maps_stock_info_to_raw_news_item(self) -> None:
        source = KiwoomStockInfoSource(client=FakeKiwoomClient(), symbols=["000660"])
        items = await source.fetch_daily(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "kiwoom")
        self.assertEqual(items[0].symbols, ["000660"])
        self.assertEqual(source.last_execution_report.item_count, 1)

    async def test_kiwoom_loader_records_partial_symbol_failures(self) -> None:
        source = KiwoomStockInfoSource(
            client=PartiallyFailingKiwoomClient(),
            symbols=["000660", "000000"],
        )
        with self.assertLogs("src.ingestion.loaders.kiwoom_loader", level="WARNING") as logs:
            items = await source.fetch_daily(
                as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00"),
                correlation=CorrelationContext(
                    correlation_id="corr_test",
                    job_id="job_test",
                    requested_by="unit_test",
                ),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(source.last_execution_report.requested_symbol_count, 2)
        self.assertEqual(source.last_execution_report.succeeded_symbol_count, 1)
        self.assertEqual(source.last_execution_report.failed_symbol_count, 1)
        self.assertTrue(source.last_execution_report.partial_success)
        self.assertIn("correlation_id=corr_test", logs.output[0])
        self.assertIn("job_id=job_test", logs.output[0])
        self.assertIn("stock_info_as_raw_item", items[0].metadata["mapping_type"])


if __name__ == "__main__":
    unittest.main()
