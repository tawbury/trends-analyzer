from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.application.use_cases.refresh_symbol_catalog import RefreshSymbolCatalogUseCase
from src.contracts.symbols import SymbolRecord
from src.db.repositories.symbol_catalog_repository import JsonSymbolCatalogRepository
from src.ingestion.catalog.json_artifact_loader import JsonArtifactSymbolCatalogSource
from src.ingestion.catalog.symbol_catalog_builder import parse_kis_master_text, parse_stock_code_csv


class StaticSymbolCatalogSource:
    source_name = "static_test"

    async def fetch_symbols(self, as_of: datetime) -> list[SymbolRecord]:
        return [
            SymbolRecord(symbol="000100", name="Low Price Stock", market="KOSPI"),
            SymbolRecord(symbol="005930", name="Samsung Electronics", market="KOSPI"),
        ]


class SymbolCatalogTest(unittest.IsolatedAsyncioTestCase):
    def test_parse_stock_code_csv_keeps_low_price_symbols(self) -> None:
        content = (
            "단축코드,한글명,시장구분\n"
            "000100,Low Price Stock,KOSPI\n"
            "005930,Samsung Electronics,KOSPI\n"
            "950001,Foreign Listing,KOSDAQ\n"
        )

        records = parse_stock_code_csv(content, allowed_markets={"KOSPI", "KOSDAQ"})

        self.assertEqual([record.symbol for record in records], ["000100", "005930", "950001"])

    def test_parse_kis_master_text_keeps_low_previous_close_symbols(self) -> None:
        tail = "ST000003500" + (" " * (184 - 11))
        content = "000100   KR7000100008Low Price Stock     " + tail

        records = parse_kis_master_text(content, market="KOSPI")

        self.assertEqual([record.symbol for record in records], ["000100"])
        self.assertEqual(records[0].metadata["previous_close"], "000003500")

    async def test_refresh_symbol_catalog_persists_latest_artifact(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repository = JsonSymbolCatalogRepository(directory=Path(temp_dir.name))
        use_case = RefreshSymbolCatalogUseCase(
            source=StaticSymbolCatalogSource(),
            repository=repository,
        )

        catalog = await use_case.execute(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )
        latest = await repository.get_latest()

        self.assertIsNotNone(latest)
        self.assertEqual(catalog.metadata["filter_policy"], "no_price_filter")
        self.assertEqual(latest.symbols, ["000100", "005930"])

    async def test_json_artifact_loader_reads_observer_shape(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        artifact = Path(temp_dir.name) / "observer_symbols.json"
        artifact.write_text(
            '{"metadata": {"count": 2}, "symbols": ["000100", "005930"]}',
            encoding="utf-8",
        )

        source = JsonArtifactSymbolCatalogSource(path=artifact)
        records = await source.fetch_symbols(
            as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00")
        )

        self.assertEqual([record.symbol for record in records], ["000100", "005930"])


if __name__ == "__main__":
    unittest.main()
