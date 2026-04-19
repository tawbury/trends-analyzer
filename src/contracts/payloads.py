from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class QTSInputPayload:
    id: str
    snapshot_id: str
    market_bias: str
    universe_adjustments: list[str]
    risk_overrides: list[str]
    sector_weights: dict[str, float]
    strategy_activation_hints: list[str]
    confidence_score: float
    generated_at: datetime
    adapter_version: str


@dataclass(frozen=True)
class GenericInsightPayload:
    id: str
    snapshot_id: str
    daily_briefing: dict
    theme_ranking: list
    watchlist_candidates: list
    alert_summary: dict
    report_seed: dict
    generated_at: datetime


@dataclass(frozen=True)
class WorkflowTriggerPayload:
    id: str
    snapshot_id: str
    trigger_type: str
    priority: str
    recommended_actions: list
    routing_conditions: dict
    downstream_payload: dict
    dispatch_policy: str
    generated_at: datetime
