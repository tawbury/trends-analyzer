from __future__ import annotations

from fastapi.testclient import TestClient
from src.api.app import create_app
import pytest
from datetime import datetime
from unittest.mock import patch
from src.shared.clock import KST

client = TestClient(create_app())

def test_device_id_middleware_generates_id():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Device-ID" in response.headers
    assert len(response.headers["X-Device-ID"]) > 0

def test_device_id_middleware_respects_header():
    test_id = "test-device-123"
    response = client.get("/api/v1/health", headers={"X-Device-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Device-ID"] == test_id

def test_market_hours_middleware_allows_get():
    # Mock is_korean_market_hours to always return True
    with patch("src.shared.middlewares.is_korean_market_hours", return_value=True):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

def test_market_hours_middleware_blocks_heavy_post():
    # Mock is_korean_market_hours to always return True
    with patch("src.shared.middlewares.is_korean_market_hours", return_value=True):
        # /api/v1/ingest/news is a heavy POST endpoint
        response = client.post("/api/v1/ingest/news")
        assert response.status_code == 403
        assert response.json()["error"] == "Market Hours Blocked"

def test_market_hours_middleware_allows_notification_token_post():
    # Mock is_korean_market_hours to always return True
    with patch("src.shared.middlewares.is_korean_market_hours", return_value=True):
        response = client.post(
            "/api/v1/notifications/tokens/anonymous",
            json={"fcm_token": "test-fcm-token"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
