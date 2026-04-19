from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.contracts.core import (
    NewsEvaluation,
    NormalizedNewsItem,
    RawNewsItem,
    TrendSnapshot,
)
from src.contracts.payloads import (
    GenericInsightPayload,
    QTSInputPayload,
    WorkflowTriggerPayload,
)
from src.contracts.runtime import AnalyzeDailyResult, CorrelationContext
from src.contracts.symbols import (
    SymbolCatalog,
    SymbolCatalogValidationReport,
    SymbolRecord,
    SymbolSelectionReport,
)


class NewsSourcePort(Protocol):
    async def fetch_daily(
        self,
        as_of: datetime,
        correlation: CorrelationContext | None = None,
    ) -> list[RawNewsItem]:
        ...


class NewsNormalizerPort(Protocol):
    def normalize(self, item: RawNewsItem) -> NormalizedNewsItem:
        ...


class NewsScorerPort(Protocol):
    def evaluate(self, item: NormalizedNewsItem, evaluated_at: datetime) -> NewsEvaluation:
        ...


class TrendAggregatorPort(Protocol):
    def aggregate(
        self,
        evaluations: list[NewsEvaluation],
        *,
        snapshot_id: str,
        as_of: datetime,
        rules_version: str,
    ) -> TrendSnapshot:
        ...


class QtsAdapterPort(Protocol):
    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> QTSInputPayload:
        ...


class GenericAdapterPort(Protocol):
    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> GenericInsightPayload:
        ...


class WorkflowAdapterPort(Protocol):
    def convert(self, snapshot: TrendSnapshot, generated_at: datetime) -> WorkflowTriggerPayload:
        ...


class SnapshotRepository(Protocol):
    async def save(self, snapshot: TrendSnapshot) -> None:
        ...

    async def get(self, snapshot_id: str) -> TrendSnapshot | None:
        ...

    async def get_latest(self) -> TrendSnapshot | None:
        ...


class QtsPayloadRepository(Protocol):
    async def save(self, payload: QTSInputPayload) -> None:
        ...

    async def get(self, payload_id: str) -> QTSInputPayload | None:
        ...

    async def get_latest(self, snapshot_id: str | None = None) -> QTSInputPayload | None:
        ...


class GenericPayloadRepository(Protocol):
    async def save(self, payload: GenericInsightPayload) -> None:
        ...

    async def get(self, payload_id: str) -> GenericInsightPayload | None:
        ...

    async def get_latest(self, snapshot_id: str | None = None) -> GenericInsightPayload | None:
        ...


class WorkflowPayloadRepository(Protocol):
    async def save(self, payload: WorkflowTriggerPayload) -> None:
        ...

    async def get(self, payload_id: str) -> WorkflowTriggerPayload | None:
        ...

    async def get_latest(self, snapshot_id: str | None = None) -> WorkflowTriggerPayload | None:
        ...


class IdempotencyRepository(Protocol):
    async def save(self, key: str, request_hash: str, result: AnalyzeDailyResult) -> None:
        ...

    async def get(self, key: str) -> tuple[str, AnalyzeDailyResult] | None:
        ...


class SymbolCatalogSourcePort(Protocol):
    async def fetch_symbols(self, as_of: datetime) -> list[SymbolRecord]:
        ...


class SymbolCatalogRepository(Protocol):
    async def save(self, catalog: SymbolCatalog) -> None:
        ...

    async def get_latest(self) -> SymbolCatalog | None:
        ...

    async def save_validation_report(self, report: SymbolCatalogValidationReport) -> None:
        ...

    async def save_selection_report(self, report: SymbolSelectionReport) -> None:
        ...
