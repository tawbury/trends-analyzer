from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.contracts.symbols import SymbolRecord
from src.ingestion.catalog.symbol_catalog_builder import records_from_symbols


class JsonArtifactSymbolCatalogSource:
    source_name = "json_artifact"

    def __init__(self, *, path: Path) -> None:
        self.path = path

    async def fetch_symbols(self, as_of: datetime) -> list[SymbolRecord]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        symbols = payload.get("symbols", payload)
        if not isinstance(symbols, list):
            raise ValueError(f"Unsupported symbol artifact shape: {self.path}")
        normalized = [
            item.get("symbol") or item.get("code") if isinstance(item, dict) else str(item)
            for item in symbols
        ]
        return records_from_symbols(normalized, source=str(self.path))
