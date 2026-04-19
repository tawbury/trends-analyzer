from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_qts_payload_repository
from src.contracts.ports import QtsPayloadRepository

router = APIRouter(tags=["qts"])


@router.get("/qts/daily-input")
async def get_qts_daily_input(
    snapshot_id: str | None = None,
    repo: QtsPayloadRepository = Depends(get_qts_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="QTS payload not found")
    return payload


@router.get("/qts/universe-adjustments")
async def get_universe_adjustments(
    snapshot_id: str | None = None,
    repo: QtsPayloadRepository = Depends(get_qts_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="QTS payload not found")
    return {"snapshot_id": payload.snapshot_id, "adjustments": payload.universe_adjustments}


@router.get("/qts/risk-overrides")
async def get_risk_overrides(
    snapshot_id: str | None = None,
    repo: QtsPayloadRepository = Depends(get_qts_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="QTS payload not found")
    return {"snapshot_id": payload.snapshot_id, "overrides": payload.risk_overrides}
