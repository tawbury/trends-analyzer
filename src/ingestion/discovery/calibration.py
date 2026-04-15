from __future__ import annotations

from dataclasses import dataclass, field

from src.ingestion.discovery.review import DiscoveryReviewItem


@dataclass(frozen=True)
class DecisionCounts:
    keep: int = 0
    weak_keep: int = 0
    drop: int = 0


@dataclass(frozen=True)
class DiscoveryCalibrationSummary:
    per_query: dict[str, DecisionCounts] = field(default_factory=dict)
    per_symbol: dict[str, DecisionCounts] = field(default_factory=dict)
    per_classification: dict[str, DecisionCounts] = field(default_factory=dict)
    noisy_alias_sample: list[str] = field(default_factory=list)
    noisy_keyword_sample: list[str] = field(default_factory=list)
    ambiguous_symbol_sample: list[str] = field(default_factory=list)


def build_calibration_summary(
    review_items: list[DiscoveryReviewItem],
) -> DiscoveryCalibrationSummary:
    per_query: dict[str, DecisionCounts] = {}
    per_symbol: dict[str, DecisionCounts] = {}
    per_classification: dict[str, DecisionCounts] = {}
    noisy_alias_sample: list[str] = []
    noisy_keyword_sample: list[str] = []
    ambiguous_symbol_sample: list[str] = []

    symbol_queries: dict[str, set[str]] = {}
    for item in review_items:
        per_query[item.query] = _increment(per_query.get(item.query, DecisionCounts()), item)
        per_symbol[item.symbol] = _increment(per_symbol.get(item.symbol, DecisionCounts()), item)
        per_classification[item.classification] = _increment(
            per_classification.get(item.classification, DecisionCounts()),
            item,
        )
        symbol_queries.setdefault(item.symbol, set()).add(item.query)
        if item.discovery_decision == "drop" and item.query_origin == "alias":
            _append_sample(noisy_alias_sample, item.query)
        if item.discovery_decision == "drop" and item.query_origin == "query_keyword":
            _append_sample(noisy_keyword_sample, item.query)

    for symbol, queries in sorted(symbol_queries.items()):
        counts = per_symbol[symbol]
        if len(queries) > 1 and counts.drop > 0 and counts.keep + counts.weak_keep > 0:
            _append_sample(ambiguous_symbol_sample, symbol)

    return DiscoveryCalibrationSummary(
        per_query=per_query,
        per_symbol=per_symbol,
        per_classification=per_classification,
        noisy_alias_sample=noisy_alias_sample,
        noisy_keyword_sample=noisy_keyword_sample,
        ambiguous_symbol_sample=ambiguous_symbol_sample,
    )


def _increment(counts: DecisionCounts, item: DiscoveryReviewItem) -> DecisionCounts:
    if item.discovery_decision == "keep":
        return DecisionCounts(
            keep=counts.keep + 1,
            weak_keep=counts.weak_keep,
            drop=counts.drop,
        )
    if item.discovery_decision == "weak_keep":
        return DecisionCounts(
            keep=counts.keep,
            weak_keep=counts.weak_keep + 1,
            drop=counts.drop,
        )
    return DecisionCounts(
        keep=counts.keep,
        weak_keep=counts.weak_keep,
        drop=counts.drop + 1,
    )


def _append_sample(items: list[str], value: str, *, limit: int = 5) -> None:
    if value not in items and len(items) < limit:
        items.append(value)
