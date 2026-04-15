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


@dataclass(frozen=True)
class DiscoveryCandidate:
    item: RawNewsItem
    record: SymbolRecord
    query: str
    dedup_key: str


@dataclass(frozen=True)
class DiscoveryFilterResult:
    items: list[RawNewsItem]
    metrics: DiscoveryQualityMetrics


def filter_discovery_candidates(
    *,
    candidates: list[DiscoveryCandidate],
    as_of: datetime,
) -> DiscoveryFilterResult:
    metrics = DiscoveryQualityMetrics()
    seen_keys: set[str] = set()
    kept_items: list[RawNewsItem] = []

    for candidate in candidates:
        metrics.record_raw(query=candidate.query)
        if candidate.dedup_key in seen_keys:
            continue
        seen_keys.add(candidate.dedup_key)
        evaluation = evaluate_discovery_item(
            item=candidate.item,
            record=candidate.record,
            query=candidate.query,
            as_of=as_of,
        )
        metrics.record_evaluation(
            query=candidate.query,
            symbol=candidate.record.symbol,
            evaluation=evaluation,
        )
        if evaluation.decision == DiscoveryDecision.DROP:
            continue
        kept_items.append(
            attach_discovery_metadata(
                item=candidate.item,
                evaluation=evaluation,
            )
        )

    return DiscoveryFilterResult(items=kept_items, metrics=metrics)
