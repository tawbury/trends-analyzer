from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import build_correlation_context, get_analyze_daily_use_case
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.api import AnalyzeDailyResponse
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext
from src.shared.clock import now_kst
from src.shared.market_hours import MarketHoursBlockedError

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])


@router.post("/daily", response_model=None)
async def analyze_daily(
    use_case: AnalyzeDailyTrendsUseCase = Depends(get_analyze_daily_use_case),
    correlation: CorrelationContext = Depends(build_correlation_context),
) -> AnalyzeDailyResponse:
    command = AnalyzeDailyCommand(as_of=now_kst(), correlation=correlation)
    try:
        result = await use_case.execute(command)
    except MarketHoursBlockedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "MARKET_HOURS_GUARD",
                    "message": "Heavy job is blocked during KST market hours.",
                    "details": {
                        "blocked_window": exc.blocked_window,
                        "job_type": exc.job_type,
                    },
                },
                "correlation_id": correlation.correlation_id,
            },
        ) from exc
    return AnalyzeDailyResponse(
        snapshot_id=result.snapshot_id,
        qts_payload_id=result.qts_payload_id,
        job_id=result.job_id,
        correlation_id=result.correlation_id,
        status="created",
    )
