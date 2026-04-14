from __future__ import annotations

import logging

from src.contracts.ports import (
    NewsNormalizerPort,
    NewsScorerPort,
    NewsSourcePort,
    QtsAdapterPort,
    QtsPayloadRepository,
    SnapshotRepository,
    TrendAggregatorPort,
)
from src.contracts.runtime import AnalyzeDailyCommand, AnalyzeDailyResult
from src.shared.logging import log_with_context
from src.shared.market_hours import assert_heavy_job_allowed

logger = logging.getLogger(__name__)


class AnalyzeDailyTrendsUseCase:
    def __init__(
        self,
        *,
        news_source: NewsSourcePort,
        normalizer: NewsNormalizerPort,
        scorer: NewsScorerPort,
        aggregator: TrendAggregatorPort,
        qts_adapter: QtsAdapterPort,
        snapshot_repository: SnapshotRepository,
        qts_payload_repository: QtsPayloadRepository,
        rules_version: str = "rules-mvp-0.1",
    ) -> None:
        self.news_source = news_source
        self.normalizer = normalizer
        self.scorer = scorer
        self.aggregator = aggregator
        self.qts_adapter = qts_adapter
        self.snapshot_repository = snapshot_repository
        self.qts_payload_repository = qts_payload_repository
        self.rules_version = rules_version

    async def execute(self, command: AnalyzeDailyCommand) -> AnalyzeDailyResult:
        assert_heavy_job_allowed(command.as_of, job_type=command.runtime_mode.value)
        log_with_context(logger, "analyze_daily_started", command.correlation)

        raw_items = await self.news_source.fetch_daily(as_of=command.as_of)
        normalized_items = [self.normalizer.normalize(item) for item in raw_items]
        evaluations = [
            self.scorer.evaluate(item, evaluated_at=command.as_of)
            for item in normalized_items
        ]
        snapshot_id = f"snapshot_{command.as_of:%Y%m%d_%H%M%S}"
        snapshot = self.aggregator.aggregate(
            evaluations,
            snapshot_id=snapshot_id,
            as_of=command.as_of,
            rules_version=self.rules_version,
        )
        await self.snapshot_repository.save(snapshot)

        qts_payload = self.qts_adapter.convert(snapshot, generated_at=command.as_of)
        await self.qts_payload_repository.save(qts_payload)

        log_with_context(logger, "analyze_daily_completed", command.correlation)
        return AnalyzeDailyResult(
            snapshot_id=snapshot.id,
            qts_payload_id=qts_payload.id,
            job_id=command.correlation.job_id,
            correlation_id=command.correlation.correlation_id,
        )
