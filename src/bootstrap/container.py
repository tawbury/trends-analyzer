from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import count
from uuid import uuid4

from src.adapters.qts.adapter import QtsAdapter
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.ports import (
    IdempotencyRepository,
    QtsPayloadRepository,
    SnapshotRepository,
)
from src.contracts.runtime import CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import MockNewsScorer
from src.db.repositories.jsonl import (
    JsonlIdempotencyRepository,
    JsonlQtsPayloadRepository,
    JsonlSnapshotRepository,
)
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource
from src.shared.config import Settings


@dataclass(frozen=True)
class Container:
    settings: Settings
    snapshot_repository: SnapshotRepository
    qts_payload_repository: QtsPayloadRepository
    idempotency_repository: IdempotencyRepository
    analyze_daily_use_case: AnalyzeDailyTrendsUseCase


_job_sequence = count(start=1)


def build_container(settings: Settings | None = None) -> Container:
    resolved_settings = settings or Settings.from_env()
    data_dir = resolved_settings.data_dir
    snapshot_repository = JsonlSnapshotRepository(data_dir / "snapshots.jsonl")
    qts_payload_repository = JsonlQtsPayloadRepository(data_dir / "qts_payloads.jsonl")
    idempotency_repository = JsonlIdempotencyRepository(data_dir / "idempotency.jsonl")

    use_case = AnalyzeDailyTrendsUseCase(
        news_source=LocalFixtureNewsSource(),
        normalizer=NewsNormalizer(),
        scorer=MockNewsScorer(),
        aggregator=TrendAggregator(),
        qts_adapter=QtsAdapter(),
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        rules_version=resolved_settings.rules_version,
    )
    return Container(
        settings=resolved_settings,
        snapshot_repository=snapshot_repository,
        qts_payload_repository=qts_payload_repository,
        idempotency_repository=idempotency_repository,
        analyze_daily_use_case=use_case,
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container()


def build_correlation_context(
    *,
    requested_by: str,
    correlation_id: str | None = None,
    job_prefix: str = "job_mvp_daily",
) -> CorrelationContext:
    sequence = next(_job_sequence)
    return CorrelationContext(
        correlation_id=correlation_id or f"corr_{uuid4().hex[:12]}",
        job_id=f"{job_prefix}_{sequence:04d}",
        requested_by=requested_by,
    )
