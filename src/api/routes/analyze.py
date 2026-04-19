from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from src.api.dependencies import (
    build_correlation_context,
    get_analyze_daily_use_case,
    verify_market_hours,
)
from src.application.use_cases.analyze_daily_trends import AnalyzeDailyTrendsUseCase
from src.contracts.runtime import AnalyzeDailyCommand, CorrelationContext, RuntimeMode

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/daily", dependencies=[Depends(verify_market_hours)])
async def analyze_daily(
    as_of: datetime | None = None,
    correlation: CorrelationContext = Depends(build_correlation_context),
    use_case: AnalyzeDailyTrendsUseCase = Depends(get_analyze_daily_use_case),
):
    target_time = as_of or datetime.now()
    command = AnalyzeDailyCommand(
        as_of=target_time,
        runtime_mode=RuntimeMode.DAILY,
        correlation=correlation,
    )
    result = await use_case.execute(command)
    return result
