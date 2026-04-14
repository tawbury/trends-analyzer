from __future__ import annotations

from datetime import datetime, timedelta

from src.contracts.core import RawNewsItem


class LocalFixtureNewsSource:
    async def fetch_daily(self, as_of: datetime) -> list[RawNewsItem]:
        collected_at = as_of
        published_at = as_of.replace(hour=6, minute=30, second=0, microsecond=0)
        if published_at > as_of:
            published_at = published_at - timedelta(days=1)
        return [
            RawNewsItem(
                id="raw_fixture_001",
                source="local_fixture",
                source_id="fixture:20260414:001",
                title="AI chip demand accelerates in Asia",
                body="Semiconductor demand growth supports AI infrastructure suppliers.",
                url="https://example.com/news/fixture-001",
                published_at=published_at,
                collected_at=collected_at,
                language="en",
                symbols=["005930", "000660"],
                metadata={"fixture": "true"},
            )
        ]
