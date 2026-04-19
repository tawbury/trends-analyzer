from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from src.adapters.brokerage_kis import KisBrokerageAdapter
from src.shared.config import Settings
from pathlib import Path

@pytest.fixture
def settings():
    return Settings(
        data_dir=Path(".local"),
        rules_version="test",
        kis_app_key="test_key",
        kis_app_secret="test_secret",
        kis_base_url="https://test.api"
    )

@pytest.mark.asyncio
async def test_kis_adapter_caching(settings):
    adapter = KisBrokerageAdapter(settings)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": {"stck_prpr": "50000"}, "api_key": "secret_key"}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        # First call - should call API
        data1 = await adapter.get_market_data("005930")
        assert data1["output"]["stck_prpr"] == "50000"
        assert "api_key" not in data1 # Sanitized
        assert mock_get.call_count == 1
        
        # Second call - should use cache
        data2 = await adapter.get_market_data("005930")
        assert data2["output"]["stck_prpr"] == "50000"
        assert mock_get.call_count == 1 # Still 1
