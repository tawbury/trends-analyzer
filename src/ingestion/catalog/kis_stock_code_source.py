from __future__ import annotations

from datetime import datetime
from io import BytesIO
from urllib.request import Request, urlopen
from zipfile import ZipFile

from src.contracts.symbols import SymbolRecord
from src.ingestion.catalog.symbol_catalog_builder import parse_kis_master_text


KIS_MASTER_ARCHIVES = {
    "KOSPI": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
    "KOSDAQ": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
    "KONEX": "https://new.real.download.dws.co.kr/common/master/konex_code.mst.zip",
}


class KisStockCodeCatalogSource:
    source_name = "kis_stock_master"

    def __init__(
        self,
        *,
        url: str,
        allowed_markets: list[str],
        timeout_seconds: float,
    ) -> None:
        self.url = url
        self.allowed_markets = {market.upper() for market in allowed_markets}
        self.timeout_seconds = timeout_seconds

    async def fetch_symbols(self, as_of: datetime) -> list[SymbolRecord]:
        records: list[SymbolRecord] = []
        for market in sorted(self.allowed_markets):
            archive_url = KIS_MASTER_ARCHIVES.get(market)
            if not archive_url:
                continue
            records.extend(
                _fetch_kis_master_archive(
                    url=archive_url,
                    market=market,
                    timeout_seconds=self.timeout_seconds,
                )
            )
        return records


def _decode(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _fetch_kis_master_archive(
    *,
    url: str,
    market: str,
    timeout_seconds: float,
) -> list[SymbolRecord]:
    request = Request(url, headers={"User-Agent": "trends-analyzer/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    with ZipFile(BytesIO(payload)) as archive:
        mst_names = [name for name in archive.namelist() if name.endswith(".mst")]
        if not mst_names:
            return []
        content = _decode(archive.read(mst_names[0]))
    return parse_kis_master_text(content, market=market)
