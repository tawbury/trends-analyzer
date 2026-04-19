from __future__ import annotations

import re

from src.contracts.symbols import SymbolRecord


_SPACE_RE = re.compile(r"\s+")
_PREFERRED_RE = re.compile(r"(\d*우[A-C]?$|우선주$|전환우선주$|상환우선주$)")
_ETF_MARKERS = ("ETF", "레버리지", "인버스", "선물")
_ETN_MARKERS = ("ETN",)
_REIT_MARKERS = ("리츠", "REIT")
_SPAC_MARKERS = ("스팩", "SPAC")
_INFRA_MARKERS = ("인프라",)
_SHIP_MARKERS = ("바다로선박", "하이골드")
_ETF_PROVIDERS = ("TIGER", "KODEX", "KBSTAR", "SOL", "ACE", "HANARO", "ARIRANG", "KOSEF")


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
        "is_holding": str("홀딩스" in name or "지주" in name).lower(),
    }
    return SymbolRecord(
        symbol=record.symbol.strip(),
        name=name,
        market=record.market.strip().upper() if record.market else "UNKNOWN",
        sector=record.sector or record.metadata.get("sector", ""),
        security_type=record.security_type.strip() or "stock",
        korean_name=record.korean_name or name,
        english_name=record.english_name or record.metadata.get("english_name", ""),
        normalized_name=normalized_name,
        aliases=aliases,
        query_keywords=query_keywords,
        metadata=metadata,
    )


def normalize_symbol_name(name: str) -> str:
    compacted = _SPACE_RE.sub("", name.strip())
    return compacted.replace("(주)", "").replace("㈜", "").replace("㈜", "")


def classify_symbol(*, name: str, security_type: str) -> str:
    upper_name = name.upper()
    st_lower = security_type.lower()
    
    # Priority 1: Explicit security type from source
    if "etf" in st_lower:
        return "etf"
    if "etn" in st_lower:
        return "etn"
    if "리츠" in st_lower or "reit" in st_lower:
        return "reit"
        
    # Priority 2: Name markers
    if any(marker in upper_name for marker in _ETN_MARKERS):
        return "etn"
    if any(marker in upper_name for marker in _ETF_MARKERS):
        return "etf"
    if any(marker.upper() in upper_name for marker in _REIT_MARKERS):
        return "reit"
    if any(marker.upper() in upper_name for marker in _SPAC_MARKERS):
        return "spac"
    if any(marker in upper_name for marker in _INFRA_MARKERS):
        return "infra"
    if any(marker in upper_name for marker in _SHIP_MARKERS):
        return "ship"
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
    
    # Holding company variants
    if "홀딩스" in name:
        candidates.append(name.replace("홀딩스", "지주"))
    elif "지주" in name:
        candidates.append(name.replace("지주", "홀딩스"))
        
    # Preferred stock base name
    if _PREFERRED_RE.search(name):
        base_name = _PREFERRED_RE.sub("", name).strip()
        if base_name:
            candidates.extend([base_name, normalize_symbol_name(base_name)])
            
    # Remove English in parentheses for aliases if present
    if "(" in name and ")" in name:
        eng_match = re.search(r"\(([^)]+)\)", name)
        if eng_match:
            base_only = name.replace(eng_match.group(0), "").strip()
            candidates.append(base_only)
            candidates.append(normalize_symbol_name(base_only))

    return _unique_non_empty(candidates)


def build_query_keywords(
    *,
    symbol: str,
    name: str,
    normalized_name: str,
    classification: str,
) -> list[str]:
    candidates = [name, normalized_name]
    
    if classification == "preferred_stock":
        base_name = _PREFERRED_RE.sub("", name).strip()
        candidates.extend([base_name, f"{base_name} 우선주", f"{base_name} 주가"])
    elif classification in {"etf", "etn", "reit", "spac", "infra"}:
        candidates.append(f"{name} {classification.upper()}")
        # For ETFs, try to extract core theme by removing provider
        if classification == "etf":
            for provider in _ETF_PROVIDERS:
                if name.upper().startswith(provider):
                    core_theme = name[len(provider):].strip()
                    if core_theme:
                        candidates.append(core_theme)
                        
    # For common stocks, also add ticker for uniqueness if name is short
    if len(name) <= 3:
        candidates.append(f"{name} {symbol}")
        
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
