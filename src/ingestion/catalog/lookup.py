from __future__ import annotations

from collections import defaultdict

from src.contracts.symbols import SymbolCatalog, SymbolRecord
from src.ingestion.catalog.normalization import normalize_symbol_name


class SymbolCatalogLookup:
    def __init__(self, catalog: SymbolCatalog) -> None:
        self.by_code = {record.symbol: record for record in catalog.records}
        self.by_name: dict[str, list[SymbolRecord]] = defaultdict(list)
        self.by_alias: dict[str, list[SymbolRecord]] = defaultdict(list)
        for record in catalog.records:
            name_key = normalize_symbol_name(record.name)
            if name_key:
                self.by_name[name_key].append(record)
            for alias in record.aliases:
                alias_key = normalize_symbol_name(alias)
                if alias_key:
                    self.by_alias[alias_key].append(record)

    def get_by_code(self, code: str) -> SymbolRecord | None:
        return self.by_code.get(code.strip())

    def find_by_name(self, name: str) -> list[SymbolRecord]:
        return _dedupe_records(self.by_name.get(normalize_symbol_name(name), []))

    def find_by_alias(self, alias: str) -> list[SymbolRecord]:
        return _dedupe_records(self.by_alias.get(normalize_symbol_name(alias), []))


def _dedupe_records(records: list[SymbolRecord]) -> list[SymbolRecord]:
    by_symbol: dict[str, SymbolRecord] = {}
    for record in records:
        by_symbol[record.symbol] = record
    return list(by_symbol.values())
