from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.shared.clock import KST

client = TestClient(app)


def test_market_hours_guard_blocks_heavy_job():
    # Mocking datetime to be during market hours (e.g., 10:00 AM KST)
    mock_now = datetime(2026, 4, 14, 10, 0, 0, tzinfo=KST)
    
    with patch("src.api.dependencies.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        response = client.post("/api/v1/ingest/news", json={})
        
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"]["code"] == "MARKET_HOURS_GUARD"


def test_market_hours_guard_allows_lightweight_job():
    # Mocking datetime to be during market hours (e.g., 10:00 AM KST)
    mock_now = datetime(2026, 4, 14, 10, 0, 0, tzinfo=KST)
    
    with patch("src.api.dependencies.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        # lightweight endpoint should be allowed
        response = client.post("/api/v1/ingest/webhook/n8n", json={})
        
        assert response.status_code == 200
