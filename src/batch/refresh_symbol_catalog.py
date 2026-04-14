from __future__ import annotations

import asyncio

from src.bootstrap.container import get_container
from src.shared.clock import now_kst
from src.shared.logging import configure_logging


async def run_refresh_symbol_catalog() -> None:
    container = get_container()
    catalog = await container.refresh_symbol_catalog_use_case.execute(as_of=now_kst())
    print(
        {
            "catalog_id": catalog.id,
            "source": catalog.source,
            "record_count": len(catalog.records),
            "artifact_dir": str(container.settings.data_dir / "symbol_catalog"),
        }
    )


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_refresh_symbol_catalog())
