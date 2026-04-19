from __future__ import annotations

import hashlib
from datetime import datetime

from src.contracts.core import RawNewsItem
from src.contracts.ports import RawNewsRepository


class IngestNewsUseCase:
    def __init__(self, raw_news_repo: RawNewsRepository) -> None:
        self.raw_news_repo = raw_news_repo

    async def execute_single(self, item: RawNewsItem) -> str:
        # Refine ID and timestamps
        collected_at = datetime.now()
        refined_id = item.id or self._generate_id(item.source, item.source_id)
        
        refined_item = RawNewsItem(
            id=refined_id,
            source=item.source,
            source_id=item.source_id,
            title=item.title,
            body=item.body,
            url=item.url,
            published_at=item.published_at,
            collected_at=collected_at,
            language=item.language,
            symbols=item.symbols,
            metadata=item.metadata,
        )

        if not await self.raw_news_repo.exists(refined_id):
            await self.raw_news_repo.save(refined_item)
            
        return refined_id

    async def execute_batch(self, items: list[RawNewsItem]) -> int:
        count = 0
        for item in items:
            await self.execute_single(item)
            count += 1
        return count

    def _generate_id(self, source: str, source_id: str) -> str:
        content = f"{source}:{source_id}".encode("utf-8")
        return f"raw_{hashlib.md5(content).hexdigest()}"
