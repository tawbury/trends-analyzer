from __future__ import annotations

import httpx
from typing import Any
from src.adapters.base import BaseBrokerageAdapter
from src.shared.config import Settings

class KisBrokerageAdapter(BaseBrokerageAdapter):
    def __init__(self, settings: Settings):
        super().__init__(ttl_seconds=settings.source_timeout_seconds)
        self.settings = settings

    async def get_market_data(self, symbol: str) -> dict[str, Any]:
        cache_key = f"kis_{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Key Injection: Server-side only
        headers = {
            "appkey": self.settings.kis_app_key,
            "appsecret": self.settings.kis_app_secret,
            "tr_id": self.settings.kis_tr_id_quote,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.settings.kis_base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                headers=headers
            )
            data = response.json()
            
            sanitized = self.sanitize_response(data)
            self._save_to_cache(cache_key, sanitized)
            return sanitized

    def sanitize_response(self, data: dict[str, Any]) -> dict[str, Any]:
        # Strip provider-specific sensitive or unnecessary fields
        sanitized = super().sanitize_response(data)
        if "msg_cd" in sanitized:
            del sanitized["msg_cd"]
        return sanitized
