from __future__ import annotations

from src.contracts.symbols import SymbolRecord


def build_symbol_news_queries(
    record: SymbolRecord,
    *,
    include_aliases: bool,
    include_query_keywords: bool,
    limit: int,
) -> list[str]:
    candidates = [
        record.korean_name or record.name,
        record.normalized_name,
    ]
    if include_aliases:
        candidates.extend(record.aliases)
    if include_query_keywords:
        candidates.extend(record.query_keywords)
    return _limit(_unique(candidates), limit)


def _limit(items: list[str], limit: int) -> list[str]:
    if limit > 0:
        return items[:limit]
    return items


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
