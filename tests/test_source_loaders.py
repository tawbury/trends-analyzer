from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any

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

    async def test_kiwoom_loader_maps_stock_info_to_raw_news_item(self) -> None:
        source = KiwoomStockInfoSource(client=FakeKiwoomClient(), symbols=["000660"])
        items = await source.fetch_daily(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "kiwoom")
        self.assertEqual(items[0].symbols, ["000660"])
        self.assertIn("stock_info_as_raw_item", items[0].metadata["mapping_type"])


if __name__ == "__main__":
    unittest.main()
