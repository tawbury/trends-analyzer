from __future__ import annotations

from src.contracts.core import RawNewsItem


class IngestNewsUseCase:
    async def execute_single(self, item: RawNewsItem) -> str:
        # Placeholder for real persistence logic
        return f"raw_{item.source_id}"

    async def execute_batch(self, items: list[RawNewsItem]) -> int:
        # Placeholder for real persistence logic
        return len(items)
