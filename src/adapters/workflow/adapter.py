from __future__ import annotations

from datetime import datetime

from src.contracts.core import TrendSnapshot
from src.contracts.payloads import WorkflowTriggerPayload


class WorkflowAdapter:
    adapter_version = "workflow-adapter-mvp-0.1"

    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> WorkflowTriggerPayload:
        market_bias = snapshot.market_signals[0].bias_hint if snapshot.market_signals else "neutral"
        return WorkflowTriggerPayload(
            id=f"wf_{snapshot.id}",
            snapshot_id=snapshot.id,
            trigger_type="daily_analysis",
            priority="high" if market_bias != "neutral" else "normal",
            recommended_actions=["dispatch_qts_payload", "send_slack_briefing"],
            routing_conditions={"market_bias": market_bias},
            downstream_payload={"snapshot_id": snapshot.id},
            dispatch_policy="immediate" if market_bias == "risk_on" else "scheduled",
            generated_at=generated_at,
        )
