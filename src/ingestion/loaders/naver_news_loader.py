from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from src.contracts.core import RawNewsItem
from src.contracts.runtime import CorrelationContext, SourceExecutionReport
from src.contracts.symbols import SymbolRecord
from src.ingestion.clients.naver_news_client import NaverNewsClient
from src.ingestion.loaders.provider_mapping import provider_metadata
from src.ingestion.loaders.query_strategy import build_symbol_news_queries
from src.shared.logging import correlation_fields

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


class NaverNewsDiscoverySource:
    source_name = "naver_news"

    def __init__(
        self,
        *,
        client: NaverNewsClient,
        symbol_records: list[SymbolRecord],
        query_limit_per_symbol: int,
        result_limit_per_query: int,
        include_aliases: bool,
        include_query_keywords: bool,
    ) -> None:
        self.client = client
        self.symbol_records = symbol_records
        self.query_limit_per_symbol = query_limit_per_symbol
        self.result_limit_per_query = result_limit_per_query
        self.include_aliases = include_aliases
        self.include_query_keywords = include_query_keywords
        self.last_execution_report = SourceExecutionReport(
            provider=self.source_name,
            requested_symbol_count=len(symbol_records),
            succeeded_symbol_count=0,
            failed_symbol_count=0,
            item_count=0,
            partial_success=False,
            failed_symbols=[],
        )

    async def fetch_daily(
        self,
        as_of: datetime,
        correlation: CorrelationContext | None = None,
    ) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []
        seen_keys: set[str] = set()
        succeeded_symbols: set[str] = set()
        failed_symbols: set[str] = set()
        failed_queries: list[str] = []
        query_count = 0

        for record in self.symbol_records:
            queries = build_symbol_news_queries(
                record,
                include_aliases=self.include_aliases,
                include_query_keywords=self.include_query_keywords,
                limit=self.query_limit_per_symbol,
            )
            symbol_had_success = False
            for query in queries:
                query_count += 1
                try:
                    response = self.client.search_news(
                        query=query,
                        display=self.result_limit_per_query,
                    )
                except Exception as exc:
                    failed_queries.append(query)
                    _log_query_failure(
                        provider=self.source_name,
                        symbol=record.symbol,
                        query=query,
                        error=str(exc),
                        correlation=correlation,
                    )
                    continue
                symbol_had_success = True
                symbol_items = _map_response_items(
                    response=response,
                    record=record,
                    query=query,
                    as_of=as_of,
                    seen_keys=seen_keys,
                )
                items.extend(symbol_items)
            if symbol_had_success:
                succeeded_symbols.add(record.symbol)
            elif queries:
                failed_symbols.add(record.symbol)

        self.last_execution_report = SourceExecutionReport(
            provider=self.source_name,
            requested_symbol_count=len(self.symbol_records),
            succeeded_symbol_count=len(succeeded_symbols),
            failed_symbol_count=len(failed_symbols),
            item_count=len(items),
            partial_success=bool(succeeded_symbols and (failed_symbols or failed_queries)),
            failed_symbols=sorted(failed_symbols),
            query_count=query_count,
            failed_query_count=len(failed_queries),
            failed_query_sample=failed_queries[:5],
        )
        if failed_symbols and not succeeded_symbols and not items:
            raise RuntimeError("Naver News source failed for all requested symbols")
        return items


def _map_response_items(
    *,
    response: dict[str, Any],
    record: SymbolRecord,
    query: str,
    as_of: datetime,
    seen_keys: set[str],
) -> list[RawNewsItem]:
    raw_items = response.get("items", [])
    if not isinstance(raw_items, list):
        return []
    mapped: list[RawNewsItem] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        description = _clean_text(item.get("description"))
        link = str(item.get("originallink") or item.get("link") or "").strip()
        dedup_key = link or title
        if not dedup_key or dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        published_at = _parse_pub_date(item.get("pubDate"), fallback=as_of)
        mapped.append(
            RawNewsItem(
                id=f"raw_naver_news_{record.symbol}_{published_at:%Y%m%d%H%M%S}_{index}",
                source="naver_news",
                source_id=f"naver:news:{record.symbol}:{dedup_key}",
                title=title or query,
                body=description or title or query,
                url=link,
                published_at=published_at,
                collected_at=as_of,
                language="ko",
                symbols=[record.symbol],
                metadata={
                    **provider_metadata("naver_news", item),
                    "query": query,
                    "symbol_name": record.name,
                    "mapping_type": "naver_news_search_result",
                },
            )
        )
    return mapped


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    return _TAG_RE.sub("", text).strip()


def _parse_pub_date(value: object, *, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError, OverflowError):
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=fallback.tzinfo)
    return parsed.astimezone(fallback.tzinfo)


def _log_query_failure(
    *,
    provider: str,
    symbol: str,
    query: str,
    error: str,
    correlation: CorrelationContext | None,
) -> None:
    fields = {
        "event": "source_query_fetch_failed",
        "source": provider,
        "symbol": symbol,
        "query": query,
        "error": error,
    }
    if correlation:
        fields.update(correlation_fields(correlation))
    logger.warning(
        "source_query_fetch_failed provider=%s symbol=%s query=%s correlation_id=%s job_id=%s error=%s",
        provider,
        symbol,
        query,
        fields.get("correlation_id", ""),
        fields.get("job_id", ""),
        error,
        extra=fields,
    )
