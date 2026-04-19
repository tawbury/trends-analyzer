from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.contracts.core import NewsCredibilityScore, NormalizedNewsItem


class NewsCredibilityEngine:
    method_version = "credibility-v0.1"

    TIER_MAPPING = {
        "official": ("tier_0_official", 0.95),
        "dart": ("tier_0_official", 0.95),
        "kis": ("tier_1_primary_market", 0.85),
        "kiwoom": ("tier_1_primary_market", 0.85),
        "reuters": ("tier_2_market_media", 0.75),
        "bloomberg": ("tier_2_market_media", 0.75),
        "rss": ("tier_3_general_media", 0.60),
        "n8n": ("tier_4_automation_inbound", 0.45),
    }

    RUMOR_KEYWORDS = [
        "루머", "추측", "관계자에 따르면", "미확인", "소문",
        "rumor", "unconfirmed", "speculation", "according to sources"
    ]

    EVIDENCE_KEYWORDS = ["공시", "발표", "확정", "데이터", "통계", "수치"]

    def calculate_scores(self, item: NormalizedNewsItem, now: datetime) -> NewsCredibilityScore:
        source_tier, source_weight = self._get_source_info(item.source)
        evidence_score = self._calculate_evidence_score(item)
        content_quality_score = self._calculate_quality_score(item)
        rumor_penalty = self._calculate_rumor_penalty(item)
        freshness_score = self._calculate_freshness_score(item, now)
        
        # Initial MVP corroboration and conflict logic
        corroboration_score = 0.2  # Single source initial state
        conflict_penalty = 0.0     # Neutral default

        confidence_score = self._apply_formula(
            source_weight=source_weight,
            evidence_score=evidence_score,
            corroboration_score=corroboration_score,
            content_quality_score=content_quality_score,
            freshness_score=freshness_score,
            conflict_penalty=conflict_penalty,
            rumor_penalty=rumor_penalty,
        )

        return NewsCredibilityScore(
            source_tier=source_tier,
            source_weight=source_weight,
            evidence_score=evidence_score,
            corroboration_score=corroboration_score,
            content_quality_score=content_quality_score,
            freshness_score=freshness_score,
            conflict_penalty=conflict_penalty,
            rumor_penalty=rumor_penalty,
            confidence_score=confidence_score,
            method_version=self.method_version,
        )

    def _get_source_info(self, source: str) -> tuple[str, float]:
        for prefix, (tier, weight) in self.TIER_MAPPING.items():
            if source.lower().startswith(prefix):
                return tier, weight
        return "tier_5_unverified", 0.25

    def _calculate_evidence_score(self, item: NormalizedNewsItem) -> float:
        score = 0.0
        if item.canonical_url:
            score += 0.4
        
        text = f"{item.normalized_title} {item.normalized_body}".lower()
        keyword_match = sum(1 for kw in self.EVIDENCE_KEYWORDS if kw in text)
        score += min(keyword_match * 0.1, 0.4)
        
        # Check for numbers/percentages
        if re.search(r"\d+%", text) or re.search(r"\d+억", text) or re.search(r"\d+조", text):
            score += 0.2
            
        return min(score, 1.0)

    def _calculate_quality_score(self, item: NormalizedNewsItem) -> float:
        body_len = len(item.normalized_body or "")
        if body_len > 500:
            return 1.0
        if body_len > 100:
            return 0.7
        if body_len > 20:
            return 0.4
        return 0.2

    def _calculate_rumor_penalty(self, item: NormalizedNewsItem) -> float:
        text = f"{item.normalized_title} {item.normalized_body}".lower()
        penalty = 0.0
        for kw in self.RUMOR_KEYWORDS:
            if kw in text:
                penalty += 0.3
        return min(penalty, 1.0)

    def _calculate_freshness_score(self, item: NormalizedNewsItem, now: datetime) -> float:
        if not item.published_at:
            return 0.5
        diff = (now - item.published_at).total_seconds()
        if diff < 3600:  # 1 hour
            return 1.0
        if diff < 86400:  # 1 day
            return 0.8
        if diff < 604800:  # 1 week
            return 0.4
        return 0.1

    def _apply_formula(
        self,
        source_weight: float,
        evidence_score: float,
        corroboration_score: float,
        content_quality_score: float,
        freshness_score: float,
        conflict_penalty: float,
        rumor_penalty: float,
    ) -> float:
        base_score = (
            source_weight * 0.35
            + evidence_score * 0.20
            + corroboration_score * 0.20
            + content_quality_score * 0.15
            + freshness_score * 0.10
        )
        penalty = (
            conflict_penalty * 0.20
            + rumor_penalty * 0.15
        )
        return round(max(0.0, min(1.0, base_score - penalty)), 4)
