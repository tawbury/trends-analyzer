from __future__ import annotations

import asyncio

from src.bootstrap.container import build_correlation_context, get_container
from src.shared.clock import now_kst
from src.shared.logging import configure_logging


async def run_source_validation() -> None:
    container = get_container()
    correlation = build_correlation_context(
        requested_by="source_validation",
        job_prefix="job_source_validation",
    )
    items = await container.news_source.fetch_daily(
        as_of=now_kst(),
        correlation=correlation,
    )
    print(f"source_item_count={len(items)}")
    for item in items:
        print(
            {
                "source": item.source,
                "source_id": item.source_id,
                "title": item.title,
                "symbols": item.symbols,
                "url": item.url,
            }
        )


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_source_validation())
