from __future__ import annotations

import logging
from datetime import datetime

from src.contracts.core import RawNewsItem
from src.contracts.ports import NewsSourcePort
from src.contracts.runtime import CorrelationContext
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
            _log("source_fetch_started", source_name, 0, correlation)
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
