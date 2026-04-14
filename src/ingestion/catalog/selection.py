from __future__ import annotations

from dataclasses import dataclass

from src.contracts.symbols import SymbolCatalog, SymbolRecord


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
    mode = policy.mode.strip().lower()
    if mode == "explicit":
        return _limit(_unique(policy.explicit_symbols), policy.limit)
    if catalog is None:
        return _limit(_unique(policy.explicit_symbols), policy.limit)
    records = catalog.records
    if mode in {"catalog_all", "all_catalog"}:
        return _limit([record.symbol for record in records], policy.limit)
    if mode in {"catalog_filtered", "filtered_catalog", "candidate"}:
        return _limit(
            [record.symbol for record in records if _matches(record, policy)],
            policy.limit,
        )
    raise ValueError(f"Unsupported source symbol policy: {policy.mode}")


def _matches(record: SymbolRecord, policy: SymbolSelectionPolicy) -> bool:
    markets = {item.upper() for item in policy.markets if item}
    classifications = {item.lower() for item in policy.classifications if item}
    classification = record.metadata.get("classification", "").lower()
    if markets and record.market.upper() not in markets:
        return False
    if classifications and classification not in classifications:
        return False
    if policy.valid_code_only and not (record.symbol.isdigit() and len(record.symbol) == 6):
        return False
    return True


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
