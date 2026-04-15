from __future__ import annotations

import hashlib
import json
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
    review_item_id: str = ""


def build_review_item(
    *,
    candidate,
    evaluation: DiscoveryEvaluation,
) -> DiscoveryReviewItem:
    record = candidate.record
    item = candidate.item
    review_item = DiscoveryReviewItem(
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
    return DiscoveryReviewItem(
        **{
            **review_item.__dict__,
            "review_item_id": build_review_item_id(review_item),
        }
    )


def build_review_item_id(item: DiscoveryReviewItem | dict) -> str:
    payload = {
        "symbol": _field(item, "symbol"),
        "query": _field(item, "query"),
        "query_origin": _field(item, "query_origin"),
        "title": _field(item, "title"),
        "url": _field(item, "url"),
        "published_at": _field(item, "published_at"),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _field(item: DiscoveryReviewItem | dict, name: str) -> str:
    if isinstance(item, dict):
        return str(item.get(name) or "")
    return str(getattr(item, name) or "")
