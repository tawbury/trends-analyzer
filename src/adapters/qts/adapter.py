from __future__ import annotations

from datetime import datetime

from src.contracts.core import TrendSnapshot
from src.contracts.payloads import QTSInputPayload


class QtsAdapter:
    adapter_version = "qts-adapter-mvp-0.1"

    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> QTSInputPayload:
        market_signal = snapshot.market_signals[0]
        candidates = [
            signal.symbol
            for signal in snapshot.stock_signals
            if signal.impact_score >= 0.6 and signal.confidence_score >= 0.6
        ]
        risk_overrides = ["manual_review_required"] if market_signal.confidence_score < 0.6 else []
        return QTSInputPayload(
            id=f"qts_{snapshot.id}",
            snapshot_id=snapshot.id,
            market_bias=market_signal.bias_hint,
            universe_adjustments=candidates,
            risk_overrides=risk_overrides,
            sector_weights=_sector_weights(snapshot),
            strategy_activation_hints=["review_ai_infrastructure"] if candidates else [],
            confidence_score=market_signal.confidence_score,
            generated_at=generated_at,
            adapter_version=self.adapter_version,
        )


def _sector_weights(snapshot: TrendSnapshot) -> dict[str, float]:
    if not snapshot.theme_signals:
        return {}
    return {
        signal.sector: round(signal.impact_score * signal.confidence_score, 4)
        for signal in snapshot.theme_signals
    }
