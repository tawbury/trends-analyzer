from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from src.contracts.core import RawNewsItem
from src.contracts.runtime import CorrelationContext, SourceExecutionReport
from src.ingestion.clients.kis_client import KisClient
from src.ingestion.loaders.provider_mapping import (
    compact_text,
    normalize_numeric_text,
    parse_provider_datetime,
    provider_metadata,
)
from src.shared.logging import correlation_fields

logger = logging.getLogger(__name__)


class KisMarketDataSource:
    source_name = "kis"

    def __init__(
        self,
        *,
        client: KisClient,
        symbols: list[str],
        invest_opinion_lookback_days: int,
        invest_opinion_limit_per_symbol: int,
    ) -> None:
        self.client = client
        self.symbols = symbols
        self.invest_opinion_lookback_days = invest_opinion_lookback_days
        self.invest_opinion_limit_per_symbol = invest_opinion_limit_per_symbol
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
                symbol_items = self._fetch_symbol_items(symbol=symbol, as_of=as_of)
            except Exception as exc:
                failed_symbols.append(symbol)
                _log_symbol_failure(
                    provider=self.source_name,
                    symbol=symbol,
                    error=str(exc),
                    correlation=correlation,
                )
                continue
            items.extend(symbol_items)
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
            raise RuntimeError(f"KIS source failed for all requested symbols: {', '.join(failed_symbols)}")
        return items

    def _fetch_symbol_items(self, *, symbol: str, as_of: datetime) -> list[RawNewsItem]:
        opinion_items = self._fetch_invest_opinion_items(symbol=symbol, as_of=as_of)
        if opinion_items:
            return opinion_items

        response = self.client.get_domestic_quote(symbol)
        output = _single_output(response)
        name = _field(output, "hts_kor_isnm", "name", fallback=symbol)
        current_price = normalize_numeric_text(_field(output, "stck_prpr", "current_price"))
        change_rate = _field(output, "prdy_ctrt", "change_rate")
        volume = _field(output, "acml_vol", "volume")
        title = f"KIS market quote signal: {name}({symbol})"
        body = compact_text(
            f"{name} current price {current_price}" if current_price else "",
            f"change rate {change_rate}%" if change_rate else "",
            f"accumulated volume {volume}" if volume else "",
        )
        return [
            RawNewsItem(
                id=f"raw_kis_{symbol}_{as_of:%Y%m%d%H%M%S}",
                source=self.source_name,
                source_id=f"kis:quote:{symbol}:{as_of:%Y%m%d}",
                title=title,
                body=body or title,
                url=f"kis://domestic-stock/quote/{symbol}",
                published_at=as_of,
                collected_at=as_of,
                language="ko",
                symbols=[symbol],
                metadata={
                    **provider_metadata("kis", response),
                    "mapping_type": "market_quote_as_raw_item",
                    "provider_endpoint": "inquire-price",
                },
            )
        ]

    def _fetch_invest_opinion_items(self, *, symbol: str, as_of: datetime) -> list[RawNewsItem]:
        end_date = as_of.strftime("%Y%m%d")
        start_date = (as_of - timedelta(days=self.invest_opinion_lookback_days)).strftime("%Y%m%d")
        response = self.client.get_invest_opinion(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        rows = _list_output(response)
        items: list[RawNewsItem] = []
        for index, row in enumerate(rows[: self.invest_opinion_limit_per_symbol], start=1):
            broker = _field(row, "mbcr_name", "broker", fallback="unknown")
            opinion = _field(row, "invt_opnn", "opinion", fallback="unknown")
            target_price = normalize_numeric_text(_field(row, "hts_goal_prc", "target_price"))
            previous_close = normalize_numeric_text(_field(row, "stck_prdy_clpr", "previous_close"))
            published_at = parse_provider_datetime(row.get("stck_bsop_date"), as_of)
            title = f"KIS investment opinion: {symbol} {opinion} by {broker}"
            body = compact_text(
                f"{broker} opinion {opinion}",
                f"target price {target_price}" if target_price else "",
                f"previous close {previous_close}" if previous_close else "",
                f"distance to target {_field(row, 'dprt', 'nday_dprt')}%" if _field(row, "dprt", "nday_dprt") else "",
            )
            items.append(
                RawNewsItem(
                    id=f"raw_kis_invest_opinion_{symbol}_{published_at:%Y%m%d}_{index}",
                    source=self.source_name,
                    source_id=f"kis:invest-opinion:{symbol}:{published_at:%Y%m%d}:{broker}:{index}",
                    title=title,
                    body=body or title,
                    url=f"kis://domestic-stock/invest-opinion/{symbol}",
                    published_at=published_at,
                    collected_at=as_of,
                    language="ko",
                    symbols=[symbol],
                    metadata={
                        **provider_metadata("kis", row),
                        "mapping_type": "investment_opinion_as_raw_item",
                        "provider_endpoint": "invest-opinion",
                        "source_response_code": _field(response, "rt_cd"),
                    },
                )
            )
        return items


def _single_output(response: dict[str, Any]) -> dict[str, Any]:
    output = response.get("output")
    if isinstance(output, dict):
        return output
    return response


def _list_output(response: dict[str, Any]) -> list[dict[str, Any]]:
    output = response.get("output")
    if not isinstance(output, list):
        return []
    return [item for item in output if isinstance(item, dict)]


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
