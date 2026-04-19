from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.shared.clock import KST
from src.shared.config import Settings

# Use a temporary directory for integration tests
TEMP_DATA_DIR = Path("./tests/tmp_integration_data")

@pytest.fixture(autouse=True)
def setup_test_env():
    if TEMP_DATA_DIR.exists():
        shutil.rmtree(TEMP_DATA_DIR)
    TEMP_DATA_DIR.mkdir(parents=True)
    
    # Mock settings to use temp data dir
    with patch.dict(os.environ, {
        "TRENDS_DATA_DIR": str(TEMP_DATA_DIR),
        "TRENDS_ACTIVE_SOURCES": "fixture",
    }):
        yield
    
    if TEMP_DATA_DIR.exists():
        shutil.rmtree(TEMP_DATA_DIR)

client = TestClient(app)

def test_full_analysis_and_retrieval_flow():
    # 1. Trigger analysis (ensure it's not market hours for heavy job)
    # Mocking datetime to be outside market hours (e.g., 6:00 PM KST)
    mock_now = datetime(2026, 4, 19, 18, 0, 0, tzinfo=KST)
    
    with patch("src.api.dependencies.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        response = client.post("/api/v1/analyze/daily")
        assert response.status_code == 200
        data = response.json()
        assert "snapshot_id" in data
        snapshot_id = data["snapshot_id"]

        # 2. Verify Signals
        response = client.get(f"/api/v1/signals/market?snapshot_id={snapshot_id}")
        assert response.status_code == 200
        market_signals = response.json()
        assert len(market_signals) > 0
        assert market_signals[0]["snapshot_id"] == snapshot_id

        # 3. Verify QTS Payload
        response = client.get(f"/api/v1/qts/daily-input?snapshot_id={snapshot_id}")
        assert response.status_code == 200
        qts_payload = response.json()
        assert qts_payload["snapshot_id"] == snapshot_id

        # 4. Verify Generic Payload
        response = client.get(f"/api/v1/generic/briefing?snapshot_id={snapshot_id}")
        assert response.status_code == 200
        briefing = response.json()
        assert "summary" in briefing

        # 5. Verify Workflow Payload
        response = client.get(f"/api/v1/workflow/payload?snapshot_id={snapshot_id}")
        assert response.status_code == 200
        wf_payload = response.json()
        assert wf_payload["snapshot_id"] == snapshot_id
