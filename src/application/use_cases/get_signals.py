from __future__ import annotations

from src.contracts.core import MarketSignal, StockSignal, ThemeSignal, TrendSnapshot
from src.contracts.ports import SnapshotRepository


class GetSignalsUseCase:
    def __init__(self, snapshot_repository: SnapshotRepository) -> None:
        self.snapshot_repository = snapshot_repository

    async def get_latest_snapshot(self) -> TrendSnapshot | None:
        return await self.snapshot_repository.get_latest()

    async def get_market_signals(self, snapshot_id: str | None = None) -> list[MarketSignal]:
        snapshot = await self._get_snapshot(snapshot_id)
        return snapshot.market_signals if snapshot else []

    async def get_theme_signals(self, snapshot_id: str | None = None) -> list[ThemeSignal]:
        snapshot = await self._get_snapshot(snapshot_id)
        return snapshot.theme_signals if snapshot else []

    async def get_stock_signals(self, snapshot_id: str | None = None) -> list[StockSignal]:
        snapshot = await self._get_snapshot(snapshot_id)
        return snapshot.stock_signals if snapshot else []

    async def _get_snapshot(self, snapshot_id: str | None) -> TrendSnapshot | None:
        if snapshot_id:
            return await self.snapshot_repository.get(snapshot_id)
        return await self.snapshot_repository.get_latest()
