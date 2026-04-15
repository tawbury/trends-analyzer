from __future__ import annotations

import logging
from datetime import datetime

from src.contracts.core import RawNewsItem
from src.contracts.ports import NewsSourcePort
from src.contracts.runtime import CorrelationContext, SourceExecutionReport
from src.shared.logging import correlation_fields

logger = logging.getLogger(__name__)


class CompositeNewsSource:
    def __init__(
        self,
        *,
        sources: list[NewsSourcePort],
        partial_success: bool,
    ) -> None:
        self.sources = sources
        self.partial_success = partial_success

    async def fetch_daily(
        self,
        as_of: datetime,
        correlation: CorrelationContext | None = None,
    ) -> list[RawNewsItem]:
        items: list[RawNewsItem] = []
        failures: list[str] = []
        for source in self.sources:
            source_name = _source_name(source)
            _log_source_start(source, source_name, correlation)
            try:
                source_items = await source.fetch_daily(as_of=as_of, correlation=correlation)
            except Exception as exc:
                failures.append(source_name)
                _log("source_fetch_failed", source_name, 0, correlation, error=str(exc))
                if not self.partial_success:
                    raise
                continue
            items.extend(source_items)
            _log("source_fetch_completed", source_name, len(source_items), correlation)
            report = getattr(source, "last_execution_report", None)
            if isinstance(report, SourceExecutionReport):
                _log_execution_report(report, correlation)

        if failures and not items:
            _log("source_fetch_all_failed", ",".join(failures), 0, correlation)
            raise RuntimeError(f"All configured sources failed: {', '.join(failures)}")
        _log("source_fetch_merged", "composite", len(items), correlation)
        return items


def _source_name(source: NewsSourcePort) -> str:
    return getattr(source, "source_name", source.__class__.__name__)


def _log(
    event: str,
    source_name: str,
    item_count: int,
    correlation: CorrelationContext | None,
    *,
    error: str | None = None,
) -> None:
    fields = {
        "event": event,
        "source": source_name,
        "item_count": str(item_count),
    }
    if correlation:
        fields.update(correlation_fields(correlation))
    if error:
        fields["error"] = error
    logger.info(
        "%s source=%s item_count=%s error=%s",
        event,
        source_name,
        item_count,
        error or "",
        extra=fields,
    )


def _log_source_start(
    source: NewsSourcePort,
    source_name: str,
    correlation: CorrelationContext | None,
) -> None:
    report = getattr(source, "symbol_selection_report", None)
    fields = {
        "event": "source_fetch_started",
        "source": source_name,
        "item_count": "0",
    }
    if correlation:
        fields.update(correlation_fields(correlation))
    if report:
        fields.update(
            {
                "catalog_id": report.catalog_id,
                "symbol_selection_policy": report.policy,
                "selected_symbol_count": str(report.selected_symbol_count),
                "catalog_invalid_code_count": str(report.catalog_invalid_code_count),
                "selection_invalid_code_excluded_count": str(
                    report.selection_invalid_code_excluded_count
                ),
                "market_filters": ",".join(report.market_filters),
                "classification_filters": ",".join(report.classification_filters),
                "explicit_override_used": str(report.explicit_override_used).lower(),
                "catalog_missing_fallback_used": str(
                    report.catalog_missing_fallback_used
                ).lower(),
            }
        )
    logger.info(
        (
            "source_fetch_started source=%s catalog_id=%s policy=%s selected_symbols=%s "
            "catalog_invalid_codes=%s selection_invalid_excluded=%s "
            "markets=%s classifications=%s explicit_override=%s catalog_missing_fallback=%s"
        ),
        source_name,
        getattr(report, "catalog_id", "") or "none",
        getattr(report, "policy", "") or "none",
        getattr(report, "selected_symbol_count", 0),
        getattr(report, "catalog_invalid_code_count", 0),
        getattr(report, "selection_invalid_code_excluded_count", 0),
        ",".join(getattr(report, "market_filters", [])),
        ",".join(getattr(report, "classification_filters", [])),
        getattr(report, "explicit_override_used", False),
        getattr(report, "catalog_missing_fallback_used", False),
        extra=fields,
    )


def _log_execution_report(
    report: SourceExecutionReport,
    correlation: CorrelationContext | None,
) -> None:
    fields = {
        "event": "source_execution_report",
        "source": report.provider,
        "requested_symbol_count": str(report.requested_symbol_count),
        "succeeded_symbol_count": str(report.succeeded_symbol_count),
        "failed_symbol_count": str(report.failed_symbol_count),
        "failed_symbol_sample": ",".join(report.failed_symbols[:5]),
        "query_count": str(report.query_count),
        "failed_query_count": str(report.failed_query_count),
        "failed_query_sample": ",".join(report.failed_query_sample[:5]),
        "raw_discovered_item_count": str(report.raw_discovered_item_count),
        "deduplicated_item_count": str(report.deduplicated_item_count),
        "kept_item_count": str(report.kept_item_count),
        "weak_keep_item_count": str(report.weak_keep_item_count),
        "dropped_item_count": str(report.dropped_item_count),
        "suspicious_item_count": str(report.suspicious_item_count),
        "top_query_yield_sample": ",".join(report.top_query_yield_sample[:5]),
        "top_symbol_yield_sample": ",".join(report.top_symbol_yield_sample[:5]),
        "top_classification_yield_sample": ",".join(
            report.top_classification_yield_sample[:5]
        ),
        "noisy_query_sample": ",".join(report.noisy_query_sample[:5]),
        "noisy_alias_sample": ",".join(report.noisy_alias_sample[:5]),
        "noisy_keyword_sample": ",".join(report.noisy_keyword_sample[:5]),
        "ambiguous_symbol_sample": ",".join(report.ambiguous_symbol_sample[:5]),
        "item_count": str(report.item_count),
        "partial_success": str(report.partial_success).lower(),
    }
    if correlation:
        fields.update(correlation_fields(correlation))
    logger.info(
        (
            "source_execution_report provider=%s requested_symbols=%s "
            "succeeded_symbols=%s failed_symbols=%s item_count=%s partial_success=%s "
            "query_count=%s failed_query_count=%s raw_discovered=%s deduplicated=%s "
            "kept=%s weak_keep=%s dropped=%s suspicious=%s "
            "failed_symbol_sample=%s failed_query_sample=%s top_query_yield=%s "
            "top_symbol_yield=%s top_classification_yield=%s noisy_query_sample=%s "
            "noisy_alias_sample=%s noisy_keyword_sample=%s ambiguous_symbol_sample=%s"
        ),
        report.provider,
        report.requested_symbol_count,
        report.succeeded_symbol_count,
        report.failed_symbol_count,
        report.item_count,
        report.partial_success,
        report.query_count,
        report.failed_query_count,
        report.raw_discovered_item_count,
        report.deduplicated_item_count,
        report.kept_item_count,
        report.weak_keep_item_count,
        report.dropped_item_count,
        report.suspicious_item_count,
        ",".join(report.failed_symbols[:5]),
        ",".join(report.failed_query_sample[:5]),
        ",".join(report.top_query_yield_sample[:5]),
        ",".join(report.top_symbol_yield_sample[:5]),
        ",".join(report.top_classification_yield_sample[:5]),
        ",".join(report.noisy_query_sample[:5]),
        ",".join(report.noisy_alias_sample[:5]),
        ",".join(report.noisy_keyword_sample[:5]),
        ",".join(report.ambiguous_symbol_sample[:5]),
        extra=fields,
    )
