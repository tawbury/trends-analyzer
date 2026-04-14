from __future__ import annotations

from datetime import datetime

from src.contracts.ports import SymbolCatalogRepository, SymbolCatalogSourcePort
from src.contracts.symbols import SymbolCatalog
from src.ingestion.catalog.normalization import enrich_symbol_record
from src.ingestion.catalog.validation import validate_symbol_catalog


class RefreshSymbolCatalogUseCase:
    def __init__(
        self,
        *,
        source: SymbolCatalogSourcePort,
        repository: SymbolCatalogRepository,
    ) -> None:
        self.source = source
        self.repository = repository

    async def execute(self, *, as_of: datetime) -> SymbolCatalog:
        source_records = await self.source.fetch_symbols(as_of=as_of)
        records = [enrich_symbol_record(record) for record in source_records]
        catalog = SymbolCatalog(
            id=f"symbol_catalog_{as_of:%Y%m%d_%H%M%S}",
            as_of=as_of,
            source=getattr(self.source, "source_name", self.source.__class__.__name__),
            records=sorted(records, key=lambda item: item.symbol),
            generated_at=as_of,
            metadata={
                "filter_policy": "no_price_filter",
                "candidate_policy": "full_catalog",
            },
        )
        await self.repository.save(catalog)
        await self.repository.save_validation_report(
            validate_symbol_catalog(catalog, generated_at=as_of)
        )
        return catalog
