from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.contracts.core import RawNewsItem
from src.contracts.symbols import SymbolRecord
from src.ingestion.discovery.evaluation import (
    DiscoveryDecision,
    attach_discovery_metadata,
    evaluate_discovery_item,
)
from src.ingestion.discovery.metrics import DiscoveryQualityMetrics
from src.ingestion.discovery.review import DiscoveryReviewItem, build_review_item
from src.ingestion.discovery.rules import DiscoveryRuleConfig


@dataclass(frozen=True)
class DiscoveryCandidate:
    item: RawNewsItem
    record: SymbolRecord
    query: str
    query_origin: str
    dedup_key: str


@dataclass(frozen=True)
class DiscoveryFilterResult:
    items: list[RawNewsItem]
    metrics: DiscoveryQualityMetrics
    review_items: list[DiscoveryReviewItem]


def filter_discovery_candidates(
    *,
    candidates: list[DiscoveryCandidate],
    as_of: datetime,
    rules: DiscoveryRuleConfig | None = None,
) -> DiscoveryFilterResult:
    resolved_rules = rules or DiscoveryRuleConfig()
    metrics = DiscoveryQualityMetrics()
    seen_keys: set[str] = set()
    kept_items: list[RawNewsItem] = []
    review_items: list[DiscoveryReviewItem] = []

    for candidate in candidates:
        metrics.record_raw(query=candidate.query)
        if candidate.dedup_key in seen_keys:
            continue
        seen_keys.add(candidate.dedup_key)
        evaluation = evaluate_discovery_item(
            item=candidate.item,
            record=candidate.record,
            query=candidate.query,
            query_origin=candidate.query_origin,
            as_of=as_of,
            rules=resolved_rules,
        )
        metrics.record_evaluation(
            query=candidate.query,
            symbol=candidate.record.symbol,
            classification=_classification(candidate.record),
            query_origin=candidate.query_origin,
            evaluation=evaluation,
        )
        review_items.append(
            build_review_item(
                candidate=candidate,
                evaluation=evaluation,
            )
        )
        if evaluation.decision == DiscoveryDecision.DROP:
            continue
        kept_items.append(
            attach_discovery_metadata(
                item=candidate.item,
                evaluation=evaluation,
            )
        )

    return DiscoveryFilterResult(
        items=kept_items,
        metrics=metrics,
        review_items=review_items,
    )


def _classification(record: SymbolRecord) -> str:
    return record.metadata.get("classification") or record.security_type or "unknown"
