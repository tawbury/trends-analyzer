from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_signals_use_case
from src.application.use_cases.get_signals import GetSignalsUseCase

router = APIRouter(tags=["signals"])


@router.get("/signals/market")
async def get_market_signals(
    snapshot_id: str | None = None,
    use_case: GetSignalsUseCase = Depends(get_signals_use_case),
):
    return await use_case.get_market_signals(snapshot_id)


@router.get("/signals/themes")
async def get_theme_signals(
    snapshot_id: str | None = None,
    use_case: GetSignalsUseCase = Depends(get_signals_use_case),
):
    return await use_case.get_theme_signals(snapshot_id)


@router.get("/signals/stocks")
async def get_stock_signals(
    snapshot_id: str | None = None,
    use_case: GetSignalsUseCase = Depends(get_signals_use_case),
):
    return await use_case.get_stock_signals(snapshot_id)
