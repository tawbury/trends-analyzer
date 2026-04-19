from __future__ import annotations

from src.contracts.core import NormalizedNewsItem, RawNewsItem


class NewsNormalizer:
    def normalize(self, item: RawNewsItem) -> NormalizedNewsItem:
        return NormalizedNewsItem(
            id=f"norm_{item.id}",
            raw_news_id=item.id,
            source=item.source,
            normalized_title=" ".join(item.title.strip().split()),
            normalized_body=" ".join(item.body.strip().split()),
            canonical_url=item.url.strip(),
            published_at=item.published_at,
            language=item.language,
            symbols=item.symbols,
        )
