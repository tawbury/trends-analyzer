from __future__ import annotations

import re

from src.contracts.symbols import SymbolRecord


_SPACE_RE = re.compile(r"\s+")
_PREFERRED_RE = re.compile(r"(\d*우[B]?$|우선주$)")
_ETF_MARKERS = ("ETF", "레버리지", "인버스", "선물")
_ETN_MARKERS = ("ETN",)
_REIT_MARKERS = ("리츠", "REIT")
_SPAC_MARKERS = ("스팩", "SPAC")


def enrich_symbol_record(record: SymbolRecord) -> SymbolRecord:
    name = record.name.strip()
    normalized_name = normalize_symbol_name(name)
    classification = classify_symbol(name=name, security_type=record.security_type)
    aliases = build_aliases(
        symbol=record.symbol,
        name=name,
        normalized_name=normalized_name,
        existing_aliases=record.aliases,
    )
    query_keywords = build_query_keywords(
        symbol=record.symbol,
        name=name,
        normalized_name=normalized_name,
        classification=classification,
    )
    metadata = {
        **record.metadata,
        "classification": classification,
        "is_preferred": str(classification == "preferred_stock").lower(),
    }
    return SymbolRecord(
        symbol=record.symbol.strip(),
        name=name,
        market=record.market.strip().upper() if record.market else "UNKNOWN",
        security_type=record.security_type.strip() or "stock",
        korean_name=record.korean_name or name,
        english_name=record.english_name,
        normalized_name=normalized_name,
        aliases=aliases,
        query_keywords=query_keywords,
        metadata=metadata,
    )


def normalize_symbol_name(name: str) -> str:
    compacted = _SPACE_RE.sub("", name.strip())
    return compacted.replace("(주)", "").replace("㈜", "")


def classify_symbol(*, name: str, security_type: str) -> str:
    upper_name = name.upper()
    if any(marker in upper_name for marker in _ETN_MARKERS):
        return "etn"
    if any(marker in upper_name for marker in _ETF_MARKERS):
        return "etf"
    if any(marker.upper() in upper_name for marker in _REIT_MARKERS):
        return "reit"
    if any(marker.upper() in upper_name for marker in _SPAC_MARKERS):
        return "spac"
    if _PREFERRED_RE.search(name):
        return "preferred_stock"
    return "stock"


def build_aliases(
    *,
    symbol: str,
    name: str,
    normalized_name: str,
    existing_aliases: list[str],
) -> list[str]:
    candidates = [name, normalized_name, symbol, *existing_aliases]
    if _PREFERRED_RE.search(name):
        base_name = _PREFERRED_RE.sub("", name).strip()
        if base_name:
            candidates.extend([base_name, normalize_symbol_name(base_name)])
    return _unique_non_empty(candidates)


def build_query_keywords(
    *,
    symbol: str,
    name: str,
    normalized_name: str,
    classification: str,
) -> list[str]:
    candidates = [name, normalized_name, symbol]
    if classification == "preferred_stock":
        base_name = _PREFERRED_RE.sub("", name).strip()
        candidates.extend([base_name, f"{base_name} 우선주"])
    elif classification in {"etf", "etn", "reit", "spac"}:
        candidates.append(f"{name} {classification.upper()}")
    return _unique_non_empty(candidates)


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
