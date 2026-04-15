from __future__ import annotations

from dataclasses import dataclass

from src.contracts.symbols import SymbolRecord


@dataclass(frozen=True)
class SymbolNewsQuery:
    query: str
    origin: str


def build_symbol_news_queries(
    record: SymbolRecord,
    *,
    include_aliases: bool,
    include_query_keywords: bool,
    limit: int,
) -> list[str]:
    return [
        query.query
        for query in build_symbol_news_query_specs(
            record,
            include_aliases=include_aliases,
            include_query_keywords=include_query_keywords,
            limit=limit,
        )
    ]


def build_symbol_news_query_specs(
    record: SymbolRecord,
    *,
    include_aliases: bool,
    include_query_keywords: bool,
    limit: int,
) -> list[SymbolNewsQuery]:
    candidates = [
        SymbolNewsQuery(
            query=record.korean_name or record.name,
            origin="korean_name" if record.korean_name else "name",
        ),
        SymbolNewsQuery(query=record.normalized_name, origin="normalized_name"),
    ]
    if include_aliases:
        candidates.extend(
            SymbolNewsQuery(query=alias, origin="alias")
            for alias in record.aliases
        )
    if include_query_keywords:
        candidates.extend(
            SymbolNewsQuery(query=keyword, origin="query_keyword")
            for keyword in record.query_keywords
        )
    return _limit(_unique(candidates), limit)


def _limit(items: list[SymbolNewsQuery], limit: int) -> list[SymbolNewsQuery]:
    if limit > 0:
        return items[:limit]
    return items


def _unique(items: list[SymbolNewsQuery]) -> list[SymbolNewsQuery]:
    seen: set[str] = set()
    result: list[SymbolNewsQuery] = []
    for item in items:
        cleaned = item.query.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(SymbolNewsQuery(query=cleaned, origin=item.origin))
    return result
