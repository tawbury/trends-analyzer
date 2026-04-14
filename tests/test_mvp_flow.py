from __future__ import annotations

import unittest
from datetime import datetime

from src.adapters.qts.adapter import QtsAdapter
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext
from src.core.aggregate import TrendAggregator
from src.core.normalize import NewsNormalizer
from src.core.score import MockNewsScorer
from src.db.repositories.memory import InMemoryQtsPayloadRepository, InMemorySnapshotRepository
from src.ingestion.loaders.local_fixture_loader import LocalFixtureNewsSource
from src.shared.market_hours import is_korean_market_hours


class MvpFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_analyze_daily_creates_snapshot_and_qts_payload(self) -> None:
        snapshots = InMemorySnapshotRepository()
        payloads = InMemoryQtsPayloadRepository()
        use_case = AnalyzeDailyTrendsUseCase(
            news_source=LocalFixtureNewsSource(),
            normalizer=NewsNormalizer(),
            scorer=MockNewsScorer(),
            aggregator=TrendAggregator(),
            qts_adapter=QtsAdapter(),
            snapshot_repository=snapshots,
            qts_payload_repository=payloads,
        )

        result = await use_case.execute(
            AnalyzeDailyCommand(
                as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00"),
                correlation=CorrelationContext(
                    correlation_id="corr_test",
                    job_id="job_test",
                    requested_by="unit_test",
                ),
            )
        )

        snapshot = await snapshots.get(result.snapshot_id)
        payload = await payloads.get(result.qts_payload_id)

        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(payload)
        self.assertEqual(result.correlation_id, "corr_test")
        self.assertEqual(payload.market_bias, "risk_on")
        self.assertIn("005930", payload.universe_adjustments)

    def test_market_hours_guard_window(self) -> None:
        self.assertTrue(is_korean_market_hours(datetime.fromisoformat("2026-04-15T10:00:00+09:00")))
        self.assertFalse(is_korean_market_hours(datetime.fromisoformat("2026-04-15T16:10:00+09:00")))


if __name__ == "__main__":
    unittest.main()
