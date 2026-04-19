from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_generic_payload_repository
from src.contracts.ports import GenericPayloadRepository

router = APIRouter(tags=["generic"])


@router.get("/generic/briefing")
async def get_briefing(
    snapshot_id: str | None = None,
    repo: GenericPayloadRepository = Depends(get_generic_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Generic insight payload not found")
    return payload.daily_briefing


@router.get("/generic/theme-ranking")
async def get_theme_ranking(
    snapshot_id: str | None = None,
    repo: GenericPayloadRepository = Depends(get_generic_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Generic insight payload not found")
    return payload.theme_ranking


@router.get("/generic/watchlist")
async def get_watchlist(
    snapshot_id: str | None = None,
    repo: GenericPayloadRepository = Depends(get_generic_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Generic insight payload not found")
    return payload.watchlist_candidates
