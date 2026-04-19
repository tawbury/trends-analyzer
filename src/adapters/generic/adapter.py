from __future__ import annotations

from datetime import datetime

from src.contracts.core import TrendSnapshot
from src.contracts.payloads import GenericInsightPayload


class GenericAdapter:
    adapter_version = "generic-adapter-mvp-0.1"

    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> GenericInsightPayload:
        return GenericInsightPayload(
            id=f"generic_{snapshot.id}",
            snapshot_id=snapshot.id,
            daily_briefing={
                "summary": f"Market analysis as of {snapshot.as_of}",
                "key_drivers": [s.bias_hint for s in snapshot.market_signals],
            },
            theme_ranking=[
                {"theme": s.theme, "rank": s.rank, "impact": s.impact_score}
                for s in snapshot.theme_signals
            ],
            watchlist_candidates=[
                {"symbol": s.symbol, "confidence": s.confidence_score}
                for s in snapshot.stock_signals
                if s.impact_score >= 0.6
            ],
            alert_summary={"count": snapshot.evaluation_count, "level": "info"},
            report_seed={"snapshot_id": snapshot.id, "rules_version": snapshot.rules_version},
            generated_at=generated_at,
        )
