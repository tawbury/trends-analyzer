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
