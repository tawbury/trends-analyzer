from __future__ import annotations

from typing import Protocol

from src.contracts.core import RawNewsItem, TrendSnapshot
from src.contracts.payloads import QTSInputPayload


class NewsSourcePort(Protocol):
    async def fetch_daily(self) -> list[RawNewsItem]:
        ...


class SnapshotRepository(Protocol):
    async def save(self, snapshot: TrendSnapshot) -> None:
        ...

    async def get(self, snapshot_id: str) -> TrendSnapshot | None:
        ...


class QtsPayloadRepository(Protocol):
    async def save(self, payload: QTSInputPayload) -> None:
        ...

    async def get(self, payload_id: str) -> QTSInputPayload | None:
        ...
