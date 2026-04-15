from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class RuntimeMode(StrEnum):
    DAILY = "daily"
    INCREMENTAL = "incremental"
    REBUILD = "rebuild"
    API_READONLY = "api_readonly"
    WEBHOOK_INBOUND = "webhook_inbound"
    WORKFLOW_DISPATCH = "workflow_dispatch"


@dataclass(frozen=True)
class CorrelationContext:
    correlation_id: str
    job_id: str
    requested_by: str


@dataclass(frozen=True)
class AnalyzeDailyCommand:
    as_of: datetime
    correlation: CorrelationContext
    runtime_mode: RuntimeMode = RuntimeMode.DAILY


@dataclass(frozen=True)
class AnalyzeDailyResult:
    snapshot_id: str
    qts_payload_id: str
    job_id: str
    correlation_id: str


@dataclass(frozen=True)
class SourceExecutionReport:
    provider: str
    requested_symbol_count: int
    succeeded_symbol_count: int
    failed_symbol_count: int
    item_count: int
    partial_success: bool
    failed_symbols: list[str]
    query_count: int = 0
    failed_query_count: int = 0
    failed_query_sample: list[str] = field(default_factory=list)
    raw_discovered_item_count: int = 0
    deduplicated_item_count: int = 0
    kept_item_count: int = 0
    weak_keep_item_count: int = 0
    dropped_item_count: int = 0
    suspicious_item_count: int = 0
    top_query_yield_sample: list[str] = field(default_factory=list)
    top_symbol_yield_sample: list[str] = field(default_factory=list)
    noisy_query_sample: list[str] = field(default_factory=list)
