from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class JsonHttpClient:
    timeout_seconds: float

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        target_url = url
        if query:
            target_url = f"{url}?{urlencode(query)}"
        return self._request_json("GET", target_url, headers=headers)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        encoded = json.dumps(body or {}).encode("utf-8")
        request_headers = {"Content-Type": "application/json;charset=UTF-8"}
        request_headers.update(headers or {})
        return self._request_json("POST", url, headers=request_headers, data=encoded)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]:
        request = Request(url=url, data=data, headers=headers or {}, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ProviderClientError(f"{method} {url} failed: {exc.code} {body}") from exc
        except URLError as exc:
            raise ProviderClientError(f"{method} {url} failed: {exc.reason}") from exc

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProviderClientError(f"{method} {url} returned non-JSON response") from exc
        if not isinstance(parsed, dict):
            raise ProviderClientError(f"{method} {url} returned unsupported JSON shape")
        return parsed
