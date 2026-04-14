from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.contracts.symbols import SymbolCatalog, SymbolRecord, SymbolSelectionReport


@dataclass(frozen=True)
class SymbolSelectionPolicy:
    mode: str
    explicit_symbols: list[str]
    markets: list[str]
    classifications: list[str]
    limit: int = 0
    valid_code_only: bool = True


def select_source_symbols(
    *,
    policy: SymbolSelectionPolicy,
    catalog: SymbolCatalog | None,
) -> list[str]:
    return [record.symbol for record in select_source_symbol_records(policy=policy, catalog=catalog)]


def build_symbol_selection_report(
    *,
    policy: SymbolSelectionPolicy,
    catalog: SymbolCatalog | None,
    generated_at: datetime,
) -> SymbolSelectionReport:
    selected_records = select_source_symbol_records(policy=policy, catalog=catalog)
    catalog_records = catalog.records if catalog is not None else []
    invalid_code_count = sum(1 for record in catalog_records if not _is_valid_symbol_code(record.symbol))
    valid_code_count = len(catalog_records) - invalid_code_count
    return SymbolSelectionReport(
        generated_at=generated_at,
        policy=policy.mode,
        catalog_id=catalog.id if catalog is not None else "",
        explicit_override_used=policy.mode.strip().lower() == "explicit" or catalog is None,
        selected_symbol_count=len(selected_records),
        selected_records=selected_records,
        catalog_total_count=len(catalog_records),
        valid_code_count=valid_code_count,
        invalid_code_excluded_count=invalid_code_count if policy.valid_code_only else 0,
        market_filters=policy.markets,
        classification_filters=policy.classifications,
        limit=policy.limit,
    )


def select_source_symbol_records(
    *,
    policy: SymbolSelectionPolicy,
    catalog: SymbolCatalog | None,
) -> list[SymbolRecord]:
    mode = policy.mode.strip().lower()
    if mode == "explicit":
        return _records_from_symbols(_limit(_unique(policy.explicit_symbols), policy.limit))
    if catalog is None:
        return _records_from_symbols(_limit(_unique(policy.explicit_symbols), policy.limit))
    records = catalog.records
    if mode in {"catalog_all", "all_catalog"}:
        return _limit_records(
            [record for record in records if _matches_code_policy(record, policy)],
            policy.limit,
        )
    if mode in {"catalog_filtered", "filtered_catalog", "candidate"}:
        return _limit_records([record for record in records if _matches(record, policy)], policy.limit)
    raise ValueError(f"Unsupported source symbol policy: {policy.mode}")


def _matches(record: SymbolRecord, policy: SymbolSelectionPolicy) -> bool:
    markets = {item.upper() for item in policy.markets if item}
    classifications = {item.lower() for item in policy.classifications if item}
    classification = record.metadata.get("classification", "").lower()
    if markets and record.market.upper() not in markets:
        return False
    if classifications and classification not in classifications:
        return False
    if not _matches_code_policy(record, policy):
        return False
    return True


def _matches_code_policy(record: SymbolRecord, policy: SymbolSelectionPolicy) -> bool:
    if policy.valid_code_only and not _is_valid_symbol_code(record.symbol):
        return False
    return True


def _is_valid_symbol_code(symbol: str) -> bool:
    return symbol.isdigit() and len(symbol) == 6


def _limit_records(records: list[SymbolRecord], limit: int) -> list[SymbolRecord]:
    unique_records = _unique_records(records)
    if limit > 0:
        return unique_records[:limit]
    return unique_records


def _limit(symbols: list[str], limit: int) -> list[str]:
    unique_symbols = _unique(symbols)
    if limit > 0:
        return unique_symbols[:limit]
    return unique_symbols


def _unique(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for symbol in symbols:
        item = symbol.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _records_from_symbols(symbols: list[str]) -> list[SymbolRecord]:
    return [
        SymbolRecord(symbol=symbol, name=symbol, market="UNKNOWN")
        for symbol in symbols
    ]


def _unique_records(records: list[SymbolRecord]) -> list[SymbolRecord]:
    seen: set[str] = set()
    result: list[SymbolRecord] = []
    for record in records:
        if not record.symbol or record.symbol in seen:
            continue
        seen.add(record.symbol)
        result.append(record)
    return result
