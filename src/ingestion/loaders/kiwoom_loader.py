from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.contracts.core import RawNewsItem
from src.contracts.runtime import CorrelationContext, SourceExecutionReport
from src.ingestion.clients.kiwoom_client import KiwoomClient
from src.ingestion.loaders.provider_mapping import (
    compact_text,
    normalize_numeric_text,
    provider_metadata,
)
from src.shared.logging import correlation_fields

logger = logging.getLogger(__name__)


class KiwoomStockInfoSource:
    source_name = "kiwoom"

    def __init__(self, *, client: KiwoomClient, symbols: list[str]) -> None:
        self.client = client
        self.symbols = symbols
        self.last_execution_report = SourceExecutionReport(
            provider=self.source_name,
            requested_symbol_count=len(symbols),
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
        succeeded_symbols: list[str] = []
        failed_symbols: list[str] = []
        for symbol in self.symbols:
            try:
                items.append(self._fetch_symbol_item(symbol=symbol, as_of=as_of))
            except Exception as exc:
                failed_symbols.append(symbol)
                _log_symbol_failure(
                    provider=self.source_name,
                    symbol=symbol,
                    error=str(exc),
                    correlation=correlation,
                )
                continue
            succeeded_symbols.append(symbol)

        self.last_execution_report = SourceExecutionReport(
            provider=self.source_name,
            requested_symbol_count=len(self.symbols),
            succeeded_symbol_count=len(succeeded_symbols),
            failed_symbol_count=len(failed_symbols),
            item_count=len(items),
            partial_success=bool(succeeded_symbols and failed_symbols),
            failed_symbols=failed_symbols,
        )
        if failed_symbols and not succeeded_symbols:
            raise RuntimeError(f"Kiwoom source failed for all requested symbols: {', '.join(failed_symbols)}")
        return items

    def _fetch_symbol_item(self, *, symbol: str, as_of: datetime) -> RawNewsItem:
        response = self.client.get_stock_info(symbol)
        output = _output(response)
        name = _field(output, "stk_nm", "name", "hts_kor_isnm", fallback=symbol)
        current_price = normalize_numeric_text(_field(output, "cur_prc", "current_price"))
        change_rate = _field(output, "flu_rt", "change_rate", "prdy_ctrt")
        volume = _field(output, "trde_qty", "volume", "acml_vol")
        title = f"Kiwoom stock info signal: {name}({symbol})"
        body = compact_text(
            f"{name} current price {current_price}" if current_price else "",
            f"change rate {change_rate}%" if change_rate else "",
            f"trade volume {volume}" if volume else "",
        )
        return RawNewsItem(
            id=f"raw_kiwoom_{symbol}_{as_of:%Y%m%d%H%M%S}",
            source=self.source_name,
            source_id=f"kiwoom:stock-info:{symbol}:{as_of:%Y%m%d}",
            title=title,
            body=body or title,
            url=f"kiwoom://domestic-stock/info/{symbol}",
            published_at=as_of,
            collected_at=as_of,
            language="ko",
            symbols=[symbol],
            metadata={
                **provider_metadata("kiwoom", response),
                "mapping_type": "stock_info_as_raw_item",
                "provider_tr": "ka10001",
            },
        )


def _output(response: dict[str, Any]) -> dict[str, Any]:
    output = response.get("output")
    if isinstance(output, dict):
        return output
    return response


def _field(payload: dict[str, Any], *names: str, fallback: str = "") -> str:
    for name in names:
        value = payload.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def _log_symbol_failure(
    *,
    provider: str,
    symbol: str,
    error: str,
    correlation: CorrelationContext | None,
) -> None:
    fields = {
        "event": "source_symbol_fetch_failed",
        "source": provider,
        "symbol": symbol,
        "error": error,
    }
    if correlation:
        fields.update(correlation_fields(correlation))
    logger.warning(
        "source_symbol_fetch_failed provider=%s symbol=%s correlation_id=%s job_id=%s error=%s",
        provider,
        symbol,
        fields.get("correlation_id", ""),
        fields.get("job_id", ""),
        error,
        extra=fields,
    )
