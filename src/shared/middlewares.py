from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.shared.clock import now_kst
from src.shared.market_hours import is_korean_market_hours


class DeviceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            # For public anonymous access, we generate a session-based UUID if missing
            # In production, we might want to return 400 if strictly required
            device_id = str(uuid.uuid4())
        
        request.state.device_id = device_id
        response = await call_next(request)
        response.headers["X-Device-ID"] = device_id
        return response


class MarketHoursMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Define heavy methods or specific endpoints to block during market hours
        is_heavy_method = request.method in ("POST", "PUT", "DELETE", "PATCH")
        
        if is_heavy_method and is_korean_market_hours(now_kst()):
            # Block heavy ingestion/modification during market hours
            # Some specific paths might be allowed (e.g., token registration)
            allowed_paths = ("/api/v1/notifications/tokens/anonymous", "/api/v1/ops/health")
            if request.url.path not in allowed_paths:
                return Response(
                    content='{"error": "Market Hours Blocked", "message": "Heavy operations are restricted during KST 09:00-15:30"}',
                    status_code=403,
                    media_type="application/json"
                )
        
        return await call_next(request)
