from __future__ import annotations

from datetime import datetime, timedelta

from src.contracts.core import MarketSignal, NewsEvaluation, StockSignal, ThemeSignal, TrendSnapshot


class TrendAggregator:
    def aggregate(
        self,
        evaluations: list[NewsEvaluation],
        *,
        snapshot_id: str,
        as_of: datetime,
        rules_version: str,
    ) -> TrendSnapshot:
        impact_score = _average([item.impact_score for item in evaluations])
        confidence_score = _average([item.confidence_score for item in evaluations])
        bias_hint = "risk_on" if impact_score >= 0.6 and confidence_score >= 0.6 else "neutral"
        themes = sorted({theme for item in evaluations for theme in item.themes})
        symbols = sorted({symbol for item in evaluations for symbol in item.symbols})
        driver_news_ids = [item.normalized_news_id for item in evaluations]

        market_signal = MarketSignal(
            id=f"market_{snapshot_id}",
            snapshot_id=snapshot_id,
            market="KR",
            bias_hint=bias_hint,
            impact_score=impact_score,
            confidence_score=confidence_score,
            driver_themes=themes,
            driver_news_ids=driver_news_ids,
            generated_at=as_of,
        )
        theme_signals = [
            ThemeSignal(
                id=f"theme_{snapshot_id}_{index}",
                snapshot_id=snapshot_id,
                theme=theme,
                sector=_sector_for_theme(theme),
                rank=index,
                momentum_score=impact_score,
                impact_score=impact_score,
                confidence_score=confidence_score,
                news_count=len(evaluations),
                driver_news_ids=driver_news_ids,
                generated_at=as_of,
            )
            for index, theme in enumerate(themes, start=1)
        ]
        stock_signals = [
            StockSignal(
                id=f"stock_{snapshot_id}_{symbol}",
                snapshot_id=snapshot_id,
                symbol=symbol,
                name=symbol,
                themes=themes,
                relevance_score=_average([item.relevance_score for item in evaluations if symbol in item.symbols]),
                sentiment_score=_average([item.sentiment_score for item in evaluations if symbol in item.symbols]),
                impact_score=_average([item.impact_score for item in evaluations if symbol in item.symbols]),
                confidence_score=_average([item.confidence_score for item in evaluations if symbol in item.symbols]),
                driver_news_ids=[item.normalized_news_id for item in evaluations if symbol in item.symbols],
                generated_at=as_of,
            )
            for symbol in symbols
        ]
        return TrendSnapshot(
            id=snapshot_id,
            as_of=as_of,
            window_start=as_of - timedelta(days=1),
            window_end=as_of,
            market_signals=[market_signal],
            theme_signals=theme_signals,
            stock_signals=stock_signals,
            evaluation_count=len(evaluations),
            rules_version=rules_version,
            created_at=as_of,
        )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _sector_for_theme(theme: str) -> str:
    if "AI" in theme:
        return "Semiconductors"
    return "General"
