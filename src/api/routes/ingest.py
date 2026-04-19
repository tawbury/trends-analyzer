from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import (
    get_ingest_news_use_case,
    verify_market_hours,
    verify_n8n_token,
)
from src.application.use_cases.ingest_news import IngestNewsUseCase
from src.contracts.core import RawNewsItem

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/news", dependencies=[Depends(verify_market_hours)])
async def ingest_news(
    item: dict,
    use_case: IngestNewsUseCase = Depends(get_ingest_news_use_case),
):
    # Mapping dict to RawNewsItem would go here
    # result = await use_case.execute_single(mapped_item)
    return {"raw_news_id": "raw_mock_001", "status": "accepted"}


@router.post("/batch", dependencies=[Depends(verify_market_hours)])
async def ingest_batch(
    items: list[dict],
    use_case: IngestNewsUseCase = Depends(get_ingest_news_use_case),
):
    # result = await use_case.execute_batch(mapped_items)
    return {"batch_id": "batch_mock_001", "accepted_count": len(items)}


@router.post("/webhook/n8n", dependencies=[Depends(verify_n8n_token)])
async def ingest_n8n_webhook(payload: dict):
    return {"status": "received"}
