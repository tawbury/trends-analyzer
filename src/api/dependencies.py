from __future__ import annotations

from fastapi import Header

from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.bootstrap.container import build_correlation_context as build_context
from src.bootstrap.container import get_container
from src.contracts.ports import IdempotencyRepository
from src.contracts.runtime import CorrelationContext


def build_correlation_context(
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
    x_requested_by: str | None = Header(default=None, alias="X-Requested-By"),
) -> CorrelationContext:
    return build_context(
        correlation_id=x_correlation_id,
        requested_by=x_requested_by or "api",
        job_prefix="job_mvp_daily",
    )


def get_analyze_daily_use_case() -> AnalyzeDailyTrendsUseCase:
    return get_container().analyze_daily_use_case


def get_idempotency_repository() -> IdempotencyRepository:
    return get_container().idempotency_repository


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    return idempotency_key
