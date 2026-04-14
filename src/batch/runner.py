from __future__ import annotations

import asyncio
from itertools import count

from src.adapters.qts.adapter import QtsAdapter
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import MockNewsScorer
from src.db.repositories.memory import InMemoryQtsPayloadRepository, InMemorySnapshotRepository
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource
from src.shared.clock import now_kst
from src.shared.logging import configure_logging

_sequence = count(start=1)


async def run_daily_job() -> None:
    use_case = AnalyzeDailyTrendsUseCase(
        news_source=LocalFixtureNewsSource(),
        normalizer=NewsNormalizer(),
        scorer=MockNewsScorer(),
        aggregator=TrendAggregator(),
        qts_adapter=QtsAdapter(),
        snapshot_repository=InMemorySnapshotRepository(),
        qts_payload_repository=InMemoryQtsPayloadRepository(),
    )
    number = next(_sequence)
    result = await use_case.execute(
        AnalyzeDailyCommand(
            as_of=now_kst(),
            correlation=CorrelationContext(
                correlation_id=f"corr_batch_{number:04d}",
                job_id=f"job_batch_daily_{number:04d}",
                requested_by="batch",
            ),
        )
    )
    print(result)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_daily_job())
