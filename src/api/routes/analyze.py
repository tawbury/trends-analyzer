from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import (
    build_correlation_context,
    get_analyze_daily_use_case,
    get_idempotency_key,
    get_idempotency_repository,
)
from src.api.errors import raise_api_error
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.api import AnalyzeDailyResponse, ErrorResponse
from src.contracts.ports import IdempotencyRepository
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext
from src.shared.clock import now_kst
from src.shared.idempotency import request_hash
from src.shared.market_hours import MarketHoursBlockedError

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])


@router.post(
    "/daily",
    response_model=AnalyzeDailyResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def analyze_daily(
    use_case: AnalyzeDailyTrendsUseCase = Depends(get_analyze_daily_use_case),
    idempotency_repository: IdempotencyRepository = Depends(get_idempotency_repository),
    idempotency_key: str | None = Depends(get_idempotency_key),
    correlation: CorrelationContext = Depends(build_correlation_context),
) -> AnalyzeDailyResponse:
    if not idempotency_key:
        raise_api_error(
            status_code=400,
            code="IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key header is required for daily analysis.",
            correlation_id=correlation.correlation_id,
        )

    daily_request_hash = request_hash(method="POST", path="/api/v1/analyze/daily")
    existing = await idempotency_repository.get(idempotency_key)
    if existing is not None:
        existing_hash, existing_result = existing
        if existing_hash != daily_request_hash:
            raise_api_error(
                status_code=409,
                code="IDEMPOTENCY_KEY_CONFLICT",
                message="Idempotency-Key was already used with a different request.",
                correlation_id=correlation.correlation_id,
            )
        return AnalyzeDailyResponse(
            snapshot_id=existing_result.snapshot_id,
            qts_payload_id=existing_result.qts_payload_id,
            job_id=existing_result.job_id,
            correlation_id=existing_result.correlation_id,
            status="replayed",
        )

    command = AnalyzeDailyCommand(as_of=now_kst(), correlation=correlation)
    try:
        result = await use_case.execute(command)
    except MarketHoursBlockedError as exc:
        raise_api_error(
            status_code=409,
            code="MARKET_HOURS_GUARD",
            message="Heavy job is blocked during KST market hours.",
            correlation_id=correlation.correlation_id,
            details={
                "blocked_window": exc.blocked_window,
                "job_type": exc.job_type,
            },
        )
    await idempotency_repository.save(idempotency_key, daily_request_hash, result)
    return AnalyzeDailyResponse(
        snapshot_id=result.snapshot_id,
        qts_payload_id=result.qts_payload_id,
        job_id=result.job_id,
        correlation_id=result.correlation_id,
        status="created",
    )
