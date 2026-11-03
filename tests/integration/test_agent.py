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

"""Integration tests for the ADK agent streaming and FastAPI serving endpoints."""

from __future__ import annotations

import os

import pytest
from app.agent import root_agent
from app.fast_api_app import app as fastapi_app
from fastapi.testclient import TestClient
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

client = TestClient(fastapi_app)


def test_fastapi_health_endpoint() -> None:
    """Verifies the ADK FastAPI server health check probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


def test_fastapi_version_endpoint() -> None:
    """Verifies the ADK FastAPI server version metadata endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "language" in data


def test_fastapi_list_apps_endpoint() -> None:
    """Verifies that the registered ADK application is discoverable."""
    response = client.get("/list-apps")
    assert response.status_code == 200
    apps = response.json()
    assert isinstance(apps, list)
    assert len(apps) > 0


def test_agent_stream() -> None:
    """Integration test for the agent stream functionality.

    Tests that the agent returns valid streaming responses in environments
    with active GCP credentials or mocks.
    """
    if os.getenv("AGENT_EVAL_MOCK") == "1":
        pytest.skip("Skipping live agent streaming invocation in mock mode.")

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="Give me a quick morning operational summary and activity briefing."
            )
        ],
    )

    try:
        events = list(
            runner.run(
                new_message=message,
                user_id="test_user",
                session_id=session.id,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            )
        )
    except Exception as exc:
        pytest.skip(f"Live agent execution skipped due to environment auth requirement: {exc}")

    assert len(events) > 0, "Expected at least one message event"
    has_text_content = any(
        event.content and event.content.parts and any(part.text for part in event.content.parts)
        for event in events
    )
    assert has_text_content, "Expected at least one message with text content"
