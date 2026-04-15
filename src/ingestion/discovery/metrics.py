from __future__ import annotations

from dataclasses import dataclass, field

from src.ingestion.discovery.evaluation import DiscoveryDecision, DiscoveryEvaluation


@dataclass
class DiscoveryQualityMetrics:
    raw_discovered_item_count: int = 0
    deduplicated_item_count: int = 0
    kept_item_count: int = 0
    weak_keep_item_count: int = 0
    dropped_item_count: int = 0
    suspicious_item_count: int = 0
    per_query_raw_count: dict[str, int] = field(default_factory=dict)
    per_query_kept_count: dict[str, int] = field(default_factory=dict)
    per_query_dropped_count: dict[str, int] = field(default_factory=dict)
    per_symbol_kept_count: dict[str, int] = field(default_factory=dict)
    noisy_query_sample: list[str] = field(default_factory=list)

    def record_raw(self, *, query: str) -> None:
        self.raw_discovered_item_count += 1
        self.per_query_raw_count[query] = self.per_query_raw_count.get(query, 0) + 1

    def record_evaluation(
        self,
        *,
        query: str,
        symbol: str,
        evaluation: DiscoveryEvaluation,
    ) -> None:
        self.deduplicated_item_count += 1
        if evaluation.decision == DiscoveryDecision.KEEP:
            self.kept_item_count += 1
            self.per_query_kept_count[query] = self.per_query_kept_count.get(query, 0) + 1
            self.per_symbol_kept_count[symbol] = self.per_symbol_kept_count.get(symbol, 0) + 1
        elif evaluation.decision == DiscoveryDecision.WEAK_KEEP:
            self.weak_keep_item_count += 1
            self.per_query_kept_count[query] = self.per_query_kept_count.get(query, 0) + 1
            self.per_symbol_kept_count[symbol] = self.per_symbol_kept_count.get(symbol, 0) + 1
        else:
            self.dropped_item_count += 1
            self.per_query_dropped_count[query] = self.per_query_dropped_count.get(query, 0) + 1
            if query not in self.noisy_query_sample and len(self.noisy_query_sample) < 5:
                self.noisy_query_sample.append(query)

        if evaluation.suspicious:
            self.suspicious_item_count += 1

    def top_query_yield_sample(self, *, limit: int = 5) -> list[str]:
        ranked = sorted(
            self.per_query_kept_count.items(),
            key=lambda item: (-item[1], item[0]),
        )
        return [f"{query}:{count}" for query, count in ranked[:limit]]

    def top_symbol_yield_sample(self, *, limit: int = 5) -> list[str]:
        ranked = sorted(
            self.per_symbol_kept_count.items(),
            key=lambda item: (-item[1], item[0]),
        )
        return [f"{symbol}:{count}" for symbol, count in ranked[:limit]]
