from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

@dataclass
class CachedResponse:
    data: Any
    expiry: datetime

@runtime_checkable
class BrokerageAdapter(Protocol):
    async def get_market_data(self, symbol: str) -> dict[str, Any]: ...
    def sanitize_response(self, data: dict[str, Any]) -> dict[str, Any]: ...

class BaseBrokerageAdapter:
    def __init__(self, ttl_seconds: int = 10):
        self._cache: dict[str, CachedResponse] = {}
        self._ttl = ttl_seconds

    def _get_from_cache(self, key: str) -> Any | None:
        cached = self._cache.get(key)
        if cached and cached.expiry > datetime.now():
            return cached.data
        return None

    def _save_to_cache(self, key: str, data: Any):
        self._cache[key] = CachedResponse(
            data=data,
            expiry=datetime.now() + timedelta(seconds=self._ttl)
        )

    def sanitize_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Default implementation that removes common sensitive fields.
        Override in specific adapters for provider-specific sanitization.
        """
        sensitive_fields = {"api_key", "secret", "internal_id", "raw_payload", "debug_info"}
        return {k: v for k, v in data.items() if k not in sensitive_fields}
