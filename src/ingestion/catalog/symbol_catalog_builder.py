from __future__ import annotations

import csv
from io import StringIO

from src.contracts.symbols import SymbolRecord
from src.ingestion.catalog.normalization import enrich_symbol_record


_MARKET_TAIL_WIDTH = {
    "KOSPI": 228,
    "KOSDAQ": 222,
    "KONEX": 184,
}

_PREVIOUS_CLOSE_OFFSET = {
    "KOSPI": 26,
    "KOSDAQ": 26,
    "KONEX": 2,
}

_LISTING_DATE_OFFSET = {
    "KOSPI": 69,
    "KOSDAQ": 66,
    "KONEX": 66,
}

_BASE_DATE_OFFSET = {
    "KOSPI": 205,
    "KOSDAQ": 201,
    "KONEX": 164,
}


def parse_kis_master_text(content: str, *, market: str) -> list[SymbolRecord]:
    records: list[SymbolRecord] = []
    normalized_market = market.upper()
    tail_width = _MARKET_TAIL_WIDTH.get(normalized_market, 184)
    for line in content.splitlines():
        row = line.rstrip("\n\r")
        if len(row) < 21 + tail_width:
            continue
        symbol = row[0:9].strip()
        standard_code = row[9:21].strip()
        name = row[21:-tail_width].strip()
        tail = row[-tail_width:]
        if not symbol or not name:
            continue
        records.append(
            enrich_symbol_record(
                SymbolRecord(
                    symbol=symbol,
                    name=name,
                    market=normalized_market,
                    security_type=tail[0:2].strip() or "stock",
                    aliases=[name],
                    metadata={
                        "standard_code": standard_code,
                        "previous_close": _tail_field(
                            tail,
                            _PREVIOUS_CLOSE_OFFSET.get(normalized_market, 2),
                            9,
                        ),
                        "listing_date": _tail_field(
                            tail,
                            _LISTING_DATE_OFFSET.get(normalized_market, 66),
                            8,
                        ),
                        "base_date": _tail_field(
                            tail,
                            _BASE_DATE_OFFSET.get(normalized_market, 164),
                            8,
                        ),
                        "source_format": "kis_master_mst",
                    },
                )
            )
        )
    return _dedupe(records)


def parse_stock_code_csv(content: str, *, allowed_markets: set[str]) -> list[SymbolRecord]:
    rows = list(csv.DictReader(StringIO(content)))
    records: list[SymbolRecord] = []
    for row in rows:
        symbol = _first(row, "단축코드", "short_code", "code", "종목코드")
        name = _first(row, "한글명", "한글 종목명", "name", "종목명")
        market = _first(row, "시장구분", "시장", "market")
        if not symbol or not name:
            continue
        if allowed_markets and market and market.upper() not in allowed_markets:
            continue
        records.append(
            enrich_symbol_record(
                SymbolRecord(
                    symbol=symbol.strip(),
                    name=name.strip(),
                    market=market.strip() if market else "UNKNOWN",
                    security_type=_first(row, "증권그룹구분", "security_type") or "stock",
                    aliases=[name.strip()],
                    metadata={
                        "source_row_market": market,
                        "raw_symbol": symbol,
                    },
                )
            )
        )
    return _dedupe(records)


def records_from_symbols(symbols: list[str], *, source: str) -> list[SymbolRecord]:
    return [
        enrich_symbol_record(
            SymbolRecord(
                symbol=symbol,
                name=symbol,
                market="UNKNOWN",
                metadata={"source": source},
            )
        )
        for symbol in sorted(set(symbols))
        if symbol
    ]


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def _tail_field(tail: str, start: int, width: int) -> str:
    return tail[start : start + width].strip()


def _dedupe(records: list[SymbolRecord]) -> list[SymbolRecord]:
    by_symbol: dict[str, SymbolRecord] = {}
    for record in records:
        by_symbol[record.symbol] = record
    return list(by_symbol.values())
