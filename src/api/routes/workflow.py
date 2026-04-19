from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_workflow_payload_repository
from src.contracts.ports import WorkflowPayloadRepository

router = APIRouter(tags=["workflow"])


@router.get("/workflow/payload")
async def get_workflow_payload(
    snapshot_id: str | None = None,
    repo: WorkflowPayloadRepository = Depends(get_workflow_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Workflow payload not found")
    return payload


@router.get("/workflow/status")
async def get_workflow_status(
    snapshot_id: str | None = None,
    repo: WorkflowPayloadRepository = Depends(get_workflow_payload_repository),
):
    payload = await repo.get_latest(snapshot_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Workflow payload not found")
    return {"id": payload.id, "priority": payload.priority, "policy": payload.dispatch_policy}
