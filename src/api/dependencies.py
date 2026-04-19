from __future__ import annotations

from fastapi import Header

from datetime import datetime

from fastapi import Header, HTTPException

from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.bootstrap.container import build_correlation_context as build_context
from src.bootstrap.container import get_container
from src.contracts.ports import IdempotencyRepository
from src.contracts.runtime import CorrelationContext
from src.shared.market_hours import MarketHoursBlockedError, assert_heavy_job_allowed


def verify_market_hours() -> None:
    try:
        assert_heavy_job_allowed(datetime.now(), "API heavy job")
    except MarketHoursBlockedError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "MARKET_HOURS_GUARD",
                    "message": str(e),
                    "details": {
                        "blocked_window": e.blocked_window,
                        "job_type": e.job_type,
                    },
                }
            },
        )


def build_correlation_context(
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
    x_requested_by: str | None = Header(default=None, alias="X-Requested-By"),
) -> CorrelationContext:
    return build_context(
        correlation_id=x_correlation_id,
        requested_by=x_requested_by or "api",
        job_prefix="job_mvp_daily",
    )


from src.application.use_cases.get_signals import GetSignalsUseCase

...

def get_analyze_daily_use_case() -> AnalyzeDailyTrendsUseCase:
    return get_container().analyze_daily_use_case


from src.application.use_cases.ingest_news import IngestNewsUseCase

...

def get_signals_use_case() -> GetSignalsUseCase:
    return get_container().get_signals_use_case


def get_ingest_news_use_case() -> IngestNewsUseCase:
    return get_container().ingest_news_use_case


from src.contracts.ports import (
    GenericPayloadRepository,
    IdempotencyRepository,
    QtsPayloadRepository,
    WorkflowPayloadRepository,
)

...

def get_idempotency_repository() -> IdempotencyRepository:
    return get_container().idempotency_repository


def get_qts_payload_repository() -> QtsPayloadRepository:
    return get_container().qts_payload_repository


def get_generic_payload_repository() -> GenericPayloadRepository:
    return get_container().generic_payload_repository


def get_workflow_payload_repository() -> WorkflowPayloadRepository:
    return get_container().workflow_payload_repository


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    return idempotency_key

import logging
logger = logging.getLogger(__name__)

def verify_n8n_token(
    x_n8n_secret: str | None = Header(default=None, alias="X-N8N-Secret"),
) -> None:
    settings = get_container().settings
    expected = settings.n8n_webhook_secret
    
    if not expected:
        logger.warning("N8N_WEBHOOK_SECRET is not configured. Webhook verification skipped.")
        return
        
    if x_n8n_secret != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "WEBHOOK_AUTH_FAILED",
                    "message": "Invalid or missing X-N8N-Secret header",
                }
            },
        )
