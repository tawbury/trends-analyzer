from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.application.use_cases.refresh_symbol_catalog import RefreshSymbolCatalogUseCase
from src.contracts.symbols import SymbolRecord
from src.db.repositories.symbol_catalog_repository import JsonSymbolCatalogRepository
from src.ingestion.catalog.json_artifact_loader import JsonArtifactSymbolCatalogSource
from src.ingestion.catalog.lookup import SymbolCatalogLookup
from src.ingestion.catalog.selection import (
    SymbolSelectionPolicy,
    build_symbol_selection_report,
    select_source_symbols,
)
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
        self.assertEqual(records[0].normalized_name, "LowPriceStock")
        self.assertIn("Low Price Stock", records[0].query_keywords)

    def test_parse_kis_master_text_keeps_low_previous_close_symbols(self) -> None:
        tail = "ST000003500" + (" " * (184 - 11))
        content = "000100   KR7000100008Low Price Stock     " + tail

        records = parse_kis_master_text(content, market="KONEX")

        self.assertEqual([record.symbol for record in records], ["000100"])
        self.assertEqual(records[0].metadata["previous_close"], "000003500")
        self.assertEqual(records[0].metadata["classification"], "stock")

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
        validation_report = Path(temp_dir.name) / "latest_symbol_catalog_validation.json"
        self.assertTrue(validation_report.exists())

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

    async def test_symbol_lookup_and_selection_use_normalized_aliases(self) -> None:
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

        lookup = SymbolCatalogLookup(catalog)
        selected = select_source_symbols(
            policy=SymbolSelectionPolicy(
                mode="catalog_filtered",
                explicit_symbols=[],
                markets=["KOSPI"],
                classifications=["stock"],
                limit=1,
                valid_code_only=True,
            ),
            catalog=catalog,
        )

        self.assertEqual(lookup.get_by_code("005930").name, "Samsung Electronics")
        self.assertEqual([record.symbol for record in lookup.find_by_alias("LowPriceStock")], ["000100"])
        self.assertEqual(selected, ["000100"])

    async def test_symbol_selection_report_counts_invalid_code_exclusions(self) -> None:
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
        catalog = type(catalog)(
            id=catalog.id,
            as_of=catalog.as_of,
            source=catalog.source,
            records=[
                *catalog.records,
                SymbolRecord(
                    symbol="KR7000100008",
                    name="Bad",
                    market="KOSPI",
                    metadata={"classification": "stock"},
                ),
            ],
            generated_at=catalog.generated_at,
            metadata=catalog.metadata,
        )

        report = build_symbol_selection_report(
            policy=SymbolSelectionPolicy(
                mode="catalog_filtered",
                explicit_symbols=[],
                markets=["KOSPI"],
                classifications=["stock"],
                valid_code_only=True,
            ),
            catalog=catalog,
            generated_at=datetime.fromisoformat("2026-04-15T16:20:00+09:00"),
        )

        self.assertEqual(report.catalog_total_count, 3)
        self.assertEqual(report.catalog_invalid_code_count, 1)
        self.assertEqual(report.selection_invalid_code_excluded_count, 1)
        self.assertEqual(report.selected_symbol_count, 2)

    async def test_selection_report_distinguishes_explicit_and_catalog_fallback(self) -> None:
        explicit_report = build_symbol_selection_report(
            policy=SymbolSelectionPolicy(
                mode="explicit",
                explicit_symbols=["005930"],
                markets=[],
                classifications=[],
            ),
            catalog=None,
            generated_at=datetime.fromisoformat("2026-04-15T16:20:00+09:00"),
        )
        fallback_report = build_symbol_selection_report(
            policy=SymbolSelectionPolicy(
                mode="catalog_filtered",
                explicit_symbols=["005930"],
                markets=["KOSPI"],
                classifications=["stock"],
            ),
            catalog=None,
            generated_at=datetime.fromisoformat("2026-04-15T16:20:00+09:00"),
        )

        self.assertTrue(explicit_report.explicit_override_used)
        self.assertFalse(explicit_report.catalog_missing_fallback_used)
        self.assertFalse(fallback_report.explicit_override_used)
        self.assertTrue(fallback_report.catalog_missing_fallback_used)

    async def test_catalog_all_policy_ignores_market_filters(self) -> None:
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

        selected = select_source_symbols(
            policy=SymbolSelectionPolicy(
                mode="catalog_all",
                explicit_symbols=[],
                markets=["KOSDAQ"],
                classifications=["etf"],
                valid_code_only=True,
            ),
            catalog=catalog,
        )

        self.assertEqual(selected, ["000100", "005930"])


if __name__ == "__main__":
    unittest.main()
