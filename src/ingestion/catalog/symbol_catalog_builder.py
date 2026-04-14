from __future__ import annotations

import csv
from io import StringIO

from src.contracts.symbols import SymbolRecord


def parse_kis_master_text(content: str, *, market: str) -> list[SymbolRecord]:
    records: list[SymbolRecord] = []
    for line in content.splitlines():
        row = line.rstrip("\n\r")
        if len(row) < 205:
            continue
        symbol = row[0:9].strip()
        standard_code = row[9:21].strip()
        name = row[21:-184].strip()
        if not symbol or not name:
            continue
        records.append(
            SymbolRecord(
                symbol=symbol,
                name=name,
                market=market.upper(),
                security_type=row[-184:-182].strip() or "stock",
                aliases=[name],
                metadata={
                    "standard_code": standard_code,
                    "previous_close": row[-182:-173].strip(),
                    "trade_stop": row[-163:-162].strip(),
                    "administrative_issue": row[-161:-160].strip(),
                    "listing_date": row[-118:-110].strip(),
                    "base_date": row[-20:-12].strip(),
                    "source_format": "kis_master_mst",
                },
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
    return _dedupe(records)


def records_from_symbols(symbols: list[str], *, source: str) -> list[SymbolRecord]:
    return [
        SymbolRecord(
            symbol=symbol,
            name=symbol,
            market="UNKNOWN",
            metadata={"source": source},
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


def _dedupe(records: list[SymbolRecord]) -> list[SymbolRecord]:
    by_symbol: dict[str, SymbolRecord] = {}
    for record in records:
        by_symbol[record.symbol] = record
    return list(by_symbol.values())
