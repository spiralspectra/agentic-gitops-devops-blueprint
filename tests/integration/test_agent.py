# Copyright 2026 The Project Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration tests for the agent service FastAPI endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agents.starter_agent.app import app

client = TestClient(app)


def test_healthz_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data


@patch("agents.starter_agent.app.get_genai_client")
def test_query_endpoint(mock_get_client):
    mock_client = MagicMock()
    mock_model_response = MagicMock()
    mock_model_response.text = "This is a mocked agent response."
    mock_client.models.generate_content.return_value = mock_model_response
    mock_get_client.return_value = mock_client

    payload = {
        "query": "Hello, how does the agent work?",
        "session_id": "test-session-123",
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "This is a mocked agent response."
    assert data["session_id"] == "test-session-123"
    assert "latency_ms" in data
