from __future__ import annotations

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

router = APIRouter(tags=["Notifications"])


class TokenRegistrationRequest(BaseModel):
    fcm_token: str


@router.post("/notifications/tokens/anonymous")
async def register_anonymous_token(
    request: Request,
    payload: TokenRegistrationRequest,
):
    device_id = request.state.device_id
    # In a real implementation, this would save to PostgreSQL
    # For now, we return a success response to verify the endpoint
    return {
        "success": True,
        "device_id": device_id,
        "message": "Token registered successfully"
    }
