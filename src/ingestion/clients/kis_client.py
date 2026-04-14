from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

from src.ingestion.clients.http import JsonHttpClient, ProviderClientError


@dataclass
class KisClient:
    base_url: str
    app_key: str
    app_secret: str
    market_division_code: str
    quote_tr_id: str
    invest_opinion_tr_id: str
    http: JsonHttpClient
    token_cache_path: Path | None = None
    _access_token: str | None = None

    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        cached = self._load_cached_token()
        if cached:
            self._access_token = cached
            return cached
        self._require_credentials()
        response = self.http.post_json(
            f"{self.base_url}/oauth2/tokenP",
            body={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise ProviderClientError("KIS token response does not include access_token")
        self._access_token = token
        self._save_cached_token(token, response)
        return token

    def get_domestic_quote(self, symbol: str) -> dict[str, Any]:
        token = self.get_access_token()
        return self.http.get_json(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers={
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": self.quote_tr_id,
                "custtype": "P",
            },
            query={
                "FID_COND_MRKT_DIV_CODE": self.market_division_code,
                "FID_INPUT_ISCD": symbol,
            },
        )

    def get_invest_opinion(
        self,
        *,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        token = self.get_access_token()
        return self.http.get_json(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/invest-opinion",
            headers={
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": self.invest_opinion_tr_id,
                "custtype": "P",
            },
            query={
                "FID_COND_MRKT_DIV_CODE": self.market_division_code,
                "FID_COND_SCR_DIV_CODE": "16633",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
            },
        )

    def _require_credentials(self) -> None:
        if not self.app_key or not self.app_secret:
            raise ProviderClientError("KIS credentials are not configured")

    def _load_cached_token(self) -> str | None:
        if self.token_cache_path is None or not self.token_cache_path.exists():
            return None
        try:
            payload = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        token = payload.get("access_token")
        expires_at = payload.get("expires_at_epoch")
        if not isinstance(token, str) or not isinstance(expires_at, int | float):
            return None
        if expires_at <= time() + 60:
            return None
        return token

    def _save_cached_token(self, token: str, response: dict[str, Any]) -> None:
        if self.token_cache_path is None:
            return
        expires_in = _expires_in_seconds(response)
        payload = {
            "access_token": token,
            "expires_at_epoch": time() + expires_in,
        }
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )


def _expires_in_seconds(response: dict[str, Any]) -> int:
    raw = response.get("expires_in") or response.get("expires_in_seconds")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 60 * 60 * 20
