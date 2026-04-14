from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.bootstrap.container import build_container
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext
from src.shared.config import Settings
from src.shared.market_hours import is_korean_market_hours


class MvpFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_analyze_daily_creates_snapshot_and_qts_payload(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        container = build_container(
            Settings(data_dir=Path(temp_dir.name), rules_version="rules-test")
        )

        result = await container.analyze_daily_use_case.execute(
            AnalyzeDailyCommand(
                as_of=datetime.fromisoformat("2026-04-15T16:10:00+09:00"),
                correlation=CorrelationContext(
                    correlation_id="corr_test",
                    job_id="job_test",
                    requested_by="unit_test",
                ),
            )
        )

        snapshot = await container.snapshot_repository.get(result.snapshot_id)
        payload = await container.qts_payload_repository.get(result.qts_payload_id)

        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(payload)
        self.assertEqual(result.correlation_id, "corr_test")
        self.assertEqual(payload.market_bias, "risk_on")
        self.assertIn("005930", payload.universe_adjustments)

        await container.idempotency_repository.save("idem-test", "request-hash", result)
        replay = await container.idempotency_repository.get("idem-test")
        self.assertIsNotNone(replay)
        replay_hash, replay_result = replay
        self.assertEqual(replay_hash, "request-hash")
        self.assertEqual(replay_result.snapshot_id, result.snapshot_id)

    def test_market_hours_guard_window(self) -> None:
        self.assertTrue(is_korean_market_hours(datetime.fromisoformat("2026-04-15T10:00:00+09:00")))
        self.assertFalse(is_korean_market_hours(datetime.fromisoformat("2026-04-15T16:10:00+09:00")))


if __name__ == "__main__":
    unittest.main()
