from __future__ import annotations

from datetime import datetime

from src.contracts.core import RawNewsItem
from src.shared.clock import now_kst


class LocalFixtureNewsSource:
    async def fetch_daily(self) -> list[RawNewsItem]:
        collected_at = now_kst()
        published_at = datetime.fromisoformat("2026-04-14T06:30:00+09:00")
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
