from __future__ import annotations

from itertools import count
from uuid import uuid4

from fastapi import Header

from src.adapters.qts.adapter import QtsAdapter
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.runtime import CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import MockNewsScorer
from src.db.repositories.memory import InMemoryQtsPayloadRepository, InMemorySnapshotRepository
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource

_job_sequence = count(start=1)
_snapshot_repository = InMemorySnapshotRepository()
_qts_payload_repository = InMemoryQtsPayloadRepository()
_use_case = AnalyzeDailyTrendsUseCase(
    news_source=LocalFixtureNewsSource(),
    normalizer=NewsNormalizer(),
    scorer=MockNewsScorer(),
    aggregator=TrendAggregator(),
    qts_adapter=QtsAdapter(),
    snapshot_repository=_snapshot_repository,
    qts_payload_repository=_qts_payload_repository,
)


def build_correlation_context(
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
    x_requested_by: str | None = Header(default=None, alias="X-Requested-By"),
) -> CorrelationContext:
    sequence = next(_job_sequence)
    return CorrelationContext(
        correlation_id=x_correlation_id or f"corr_{uuid4().hex[:12]}",
        job_id=f"job_mvp_daily_{sequence:04d}",
        requested_by=x_requested_by or "api",
    )


def get_analyze_daily_use_case() -> AnalyzeDailyTrendsUseCase:
    return _use_case
