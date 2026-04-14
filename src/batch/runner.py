from __future__ import annotations

import asyncio

from src.bootstrap.container import build_correlation_context, get_container
from src.contracts.runtime import AnalyzeDailyCommand
from src.shared.clock import now_kst
from src.shared.logging import configure_logging


async def run_daily_job() -> None:
    container = get_container()
    result = await container.analyze_daily_use_case.execute(
        AnalyzeDailyCommand(
            as_of=now_kst(),
            correlation=build_correlation_context(
                requested_by="batch",
                job_prefix="job_batch_daily",
            ),
        )
    )
    print(result)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_daily_job())
