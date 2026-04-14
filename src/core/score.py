from __future__ import annotations

from datetime import datetime

from src.contracts.core import NewsEvaluation, NormalizedNewsItem


class MockNewsScorer:
    def evaluate(self, item: NormalizedNewsItem, evaluated_at: datetime) -> NewsEvaluation:
        text = f"{item.normalized_title} {item.normalized_body}".lower()
        ai_theme = "ai" in text or "chip" in text or "semiconductor" in text
        impact = 0.75 if ai_theme else 0.45
        confidence = 0.72 if item.canonical_url else 0.5
        sentiment = 0.65 if any(word in text for word in ("growth", "demand", "accelerates")) else 0.5
        themes = ["AI infrastructure"] if ai_theme else ["General market"]
        sectors = ["Semiconductors"] if ai_theme else ["General"]
        return NewsEvaluation(
            id=f"eval_{item.id}",
            normalized_news_id=item.id,
            relevance_score=0.8 if item.symbols else 0.55,
            sentiment_score=sentiment,
            impact_score=impact,
            confidence_score=confidence,
            novelty_score=0.6,
            source_weight=0.7,
            themes=themes,
            sectors=sectors,
            symbols=item.symbols,
            evaluated_at=evaluated_at,
        )
