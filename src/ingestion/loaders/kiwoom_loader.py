from __future__ import annotations

from datetime import datetime
from typing import Any

from src.contracts.core import RawNewsItem
from src.contracts.runtime import CorrelationContext
from src.ingestion.clients.kiwoom_client import KiwoomClient
from src.ingestion.loaders.provider_mapping import (
    compact_text,
    normalize_numeric_text,
    provider_metadata,
)


class KiwoomStockInfoSource:
    source_name = "kiwoom"

    def __init__(self, *, client: KiwoomClient, symbols: list[str]) -> None:
        self.client = client
        self.symbols = symbols

    async def fetch_daily(
        self,
        as_of: datetime,
        correlation: CorrelationContext | None = None,
    ) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []
        for symbol in self.symbols:
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
            items.append(
                RawNewsItem(
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
            )
        return items


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
