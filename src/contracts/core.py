from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawNewsItem:
    id: str
    source: str
    source_id: str
    title: str
    body: str
    url: str
    published_at: datetime
    collected_at: datetime
    language: str = "en"
    symbols: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedNewsItem:
    id: str
    raw_news_id: str
    source: str
    normalized_title: str
    normalized_body: str
    canonical_url: str
    published_at: datetime
    language: str
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsCredibilityScore:
    source_tier: str
    source_weight: float
    evidence_score: float
    corroboration_score: float
    content_quality_score: float
    freshness_score: float
    conflict_penalty: float
    rumor_penalty: float
    confidence_score: float
    method_version: str


@dataclass(frozen=True)
class NewsEvaluation:
    id: str
    normalized_news_id: str
    relevance_score: float
    sentiment_score: float
    impact_score: float
    confidence_score: float
    novelty_score: float
    source_weight: float
    urgency_score: float = 0.0
    actionability_score: float = 0.0
    content_value_score: float = 0.0
    credibility_breakdown: dict[str, float | str] = field(default_factory=dict)
    themes: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class MarketSignal:
    id: str
    snapshot_id: str
    market: str
    bias_hint: str
    impact_score: float
    confidence_score: float
    driver_themes: list[str]
    driver_news_ids: list[str]
    generated_at: datetime


@dataclass(frozen=True)
class ThemeSignal:
    id: str
    snapshot_id: str
    theme: str
    sector: str
    rank: int
    momentum_score: float
    impact_score: float
    confidence_score: float
    news_count: int
    driver_news_ids: list[str]
    generated_at: datetime


@dataclass(frozen=True)
class StockSignal:
    id: str
    snapshot_id: str
    symbol: str
    name: str
    themes: list[str]
    relevance_score: float
    sentiment_score: float
    impact_score: float
    confidence_score: float
    driver_news_ids: list[str]
    generated_at: datetime


@dataclass(frozen=True)
class TrendSnapshot:
    id: str
    as_of: datetime
    window_start: datetime
    window_end: datetime
    market_signals: list[MarketSignal]
    theme_signals: list[ThemeSignal]
    stock_signals: list[StockSignal]
    evaluation_count: int
    rules_version: str
    created_at: datetime
