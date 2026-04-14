from __future__ import annotations

from src.contracts.core import TrendSnapshot
from src.contracts.payloads import QTSInputPayload


class InMemorySnapshotRepository:
    def __init__(self) -> None:
        self._items: dict[str, TrendSnapshot] = {}

    async def save(self, snapshot: TrendSnapshot) -> None:
        self._items[snapshot.id] = snapshot

    async def get(self, snapshot_id: str) -> TrendSnapshot | None:
        return self._items.get(snapshot_id)


class InMemoryQtsPayloadRepository:
    def __init__(self) -> None:
        self._items: dict[str, QTSInputPayload] = {}

    async def save(self, payload: QTSInputPayload) -> None:
        self._items[payload.id] = payload

    async def get(self, payload_id: str) -> QTSInputPayload | None:
        return self._items.get(payload_id)
