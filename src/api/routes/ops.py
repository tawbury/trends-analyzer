from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/jobs/status")
async def get_jobs_status():
    return []
