from __future__ import annotations

from datetime import datetime

import pytest

from src.contracts.core import NormalizedNewsItem
from src.core.credibility import NewsCredibilityEngine
from src.shared.clock import KST


@pytest.fixture
def engine():
    return NewsCredibilityEngine()


def test_official_news_high_confidence(engine):
    now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=KST)
    item = NormalizedNewsItem(
        id="news_001",
        raw_news_id="raw_001",
        source="official:dart",
        normalized_title="Samsung Electronics Quarterly Report",
        normalized_body="Revenue increased by 15% to 70 trillion won. Official IR release.",
        canonical_url="https://dart.fss.or.kr/123",
        published_at=now,
        language="ko",
        symbols=["005930"],
    )
    
    score = engine.calculate_scores(item, now)
    
    assert score.source_tier == "tier_0_official"
    assert score.source_weight == 0.95
    assert score.evidence_score >= 0.6  # URL + keywords + numbers
    assert score.rumor_penalty == 0.0
    assert score.confidence_score >= 0.65  # 0.95*0.35 + 0.6*0.2 + 0.2*0.2 + 0.7*0.15 + 1.0*0.1 = 0.3325 + 0.12 + 0.04 + 0.105 + 0.1 = 0.6975


def test_rumor_news_low_confidence(engine):
    now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=KST)
    item = NormalizedNewsItem(
        id="news_002",
        raw_news_id="raw_002",
        source="rss:blog",
        normalized_title="Apple Car rumor",
        normalized_body="According to sources, Apple is testing a new car. This is just a rumor.",
        canonical_url="",
        published_at=now,
        language="en",
        symbols=["AAPL"],
    )
    
    score = engine.calculate_scores(item, now)
    
    assert score.source_tier == "tier_3_general_media"
    assert score.rumor_penalty >= 0.3
    assert score.confidence_score < 0.5


def test_unverified_short_news(engine):
    now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=KST)
    item = NormalizedNewsItem(
        id="news_003",
        raw_news_id="raw_003",
        source="unknown",
        normalized_title="Something happened",
        normalized_body="Short text.",
        canonical_url="",
        published_at=now,
        language="en",
        symbols=[],
    )
    
    score = engine.calculate_scores(item, now)
    
    assert score.source_tier == "tier_5_unverified"
    assert score.content_quality_score <= 0.4
    assert score.confidence_score < 0.3

def test_corroboration_score_calculation(engine):
    now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=KST)
    item1 = NormalizedNewsItem(
        id="n1", raw_news_id="r1", source="Reuters", normalized_title="T1", normalized_body="B1",
        canonical_url="", published_at=now, language="en", dedup_key="cluster1", symbols=[]
    )
    item2 = NormalizedNewsItem(
        id="n2", raw_news_id="r2", source="Bloomberg", normalized_title="T1", normalized_body="B1",
        canonical_url="", published_at=now, language="en", dedup_key="cluster1", symbols=[]
    )
    item3 = NormalizedNewsItem(
        id="n3", raw_news_id="r3", source="Official:Dart", normalized_title="T1", normalized_body="B1",
        canonical_url="", published_at=now, language="ko", dedup_key="cluster1", symbols=[]
    )
    
    # N=1
    score1 = engine.calculate_corroboration_score([item1])
    assert score1 == 0.2
    
    # N=2
    score2 = engine.calculate_corroboration_score([item1, item2])
    assert score2 == 0.5
    
    # N=3
    score3 = engine.calculate_corroboration_score([item1, item2, item3])
    assert score3 == 0.7
    
    # N=1 (but multiple items from same source)
    item4 = NormalizedNewsItem(
        id="n4", raw_news_id="r4", source="Reuters", normalized_title="T1", normalized_body="B1",
        canonical_url="", published_at=now, language="en", dedup_key="cluster1", symbols=[]
    )
    score4 = engine.calculate_corroboration_score([item1, item4])
    assert score4 == 0.2


def test_confidence_boost_by_corroboration(engine):
    now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=KST)
    item = NormalizedNewsItem(
        id="n1", raw_news_id="r1", source="rss:news", normalized_title="Market Up", normalized_body="Stock market is going up today.",
        canonical_url="http://news.com", published_at=now, language="en", symbols=[]
    )
    
    # Baseline (no corroboration score provided, defaults to 0.2)
    score_baseline = engine.calculate_scores(item, now)
    
    # Boosted (corroboration score 1.0)
    score_boosted = engine.calculate_scores(item, now, corroboration_score=1.0)
    
    assert score_boosted.confidence_score > score_baseline.confidence_score
    # Difference should be (1.0 - 0.2) * 0.2 = 0.16
    assert round(score_boosted.confidence_score - score_baseline.confidence_score, 4) == 0.16
