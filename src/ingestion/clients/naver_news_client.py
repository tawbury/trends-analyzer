from __future__ import annotations

from typing import Any

from src.ingestion.clients.http import JsonHttpClient, ProviderClientError


class NaverNewsClient:
    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        http: JsonHttpClient,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = http

    def search_news(
        self,
        *,
        query: str,
        display: int,
        start: int = 1,
        sort: str = "date",
    ) -> dict[str, Any]:
        if not self.client_id or not self.client_secret:
            raise ProviderClientError("Naver News credentials are required")
        return self.http.get_json(
            f"{self.base_url}/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
            query={
                "query": query,
                "display": str(display),
                "start": str(start),
                "sort": sort,
            },
        )
