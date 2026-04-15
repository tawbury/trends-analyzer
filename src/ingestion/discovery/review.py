from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.discovery.evaluation import DiscoveryEvaluation


@dataclass(frozen=True)
class DiscoveryReviewItem:
    symbol: str
    query: str
    query_origin: str
    title: str
    url: str
    published_at: str
    discovery_decision: str
    discovery_score: float
    discovery_reasons: list[str]
    discovery_suspicious: bool
    classification: str


def build_review_item(
    *,
    candidate,
    evaluation: DiscoveryEvaluation,
) -> DiscoveryReviewItem:
    record = candidate.record
    item = candidate.item
    return DiscoveryReviewItem(
        symbol=record.symbol,
        query=candidate.query,
        query_origin=candidate.query_origin,
        title=item.title,
        url=item.url,
        published_at=item.published_at.isoformat(),
        discovery_decision=evaluation.decision.value,
        discovery_score=evaluation.score,
        discovery_reasons=evaluation.reasons,
        discovery_suspicious=evaluation.suspicious,
        classification=record.metadata.get("classification") or record.security_type or "unknown",
    )
