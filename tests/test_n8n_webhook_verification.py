from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.shared.config import Settings

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_secret(monkeypatch):
    secret = "test-n8n-secret-123"
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", secret)
    # Re-initialize container/settings for test
    from src.bootstrap.container import build_container
    from src.api.app import app
    # This is a bit tricky with global container, but let's see if setting env is enough
    return secret

def test_webhook_unauthorized_missing_header(client, mock_secret):
    response = client.post("/api/v1/ingest/webhook/n8n", json={"data": "test"})
    # If N8N_WEBHOOK_SECRET is set, missing header should fail
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "WEBHOOK_AUTH_FAILED"

def test_webhook_unauthorized_wrong_secret(client, mock_secret):
    headers = {"X-N8N-Secret": "wrong-secret"}
    response = client.post("/api/v1/ingest/webhook/n8n", json={"data": "test"}, headers=headers)
    assert response.status_code == 401

def test_webhook_authorized_success(client, mock_secret):
    headers = {"X-N8N-Secret": mock_secret}
    response = client.post("/api/v1/ingest/webhook/n8n", json={"data": "test"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
