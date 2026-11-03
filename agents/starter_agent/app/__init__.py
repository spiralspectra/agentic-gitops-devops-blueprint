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

"""Starter Agent Application Package."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from google import genai

from app.agent import app, root_agent
from app.core.config import GCP_PROJECT_ID, GCP_REGION

logger = logging.getLogger(__name__)

fastapi_app = app  # Alias for FastAPI application instance

SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"reveal (the )?system prompt", re.IGNORECASE),
    re.compile(r"system\.root_password", re.IGNORECASE),
    re.compile(r"drop table ", re.IGNORECASE),
]


def is_safe_input(prompt: str) -> bool:
    """Evaluates whether an incoming query violates safety guardrails."""
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(prompt):
            return False
    return True


def format_telemetry_event(
    session_id: str, query: str, duration_ms: float
) -> dict[str, Any]:
    """Formats structured telemetry log event for BigQuery / Cloud Logging."""
    return {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "query_length": len(query),
        "duration_ms": duration_ms,
        "status": "success" if duration_ms < 5000.0 else "slow",
    }


def get_genai_client() -> genai.Client:
    """Initializes Google GenAI client configured with Vertex AI backend."""
    return genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location=GCP_REGION,
    )


__all__ = [
    "app",
    "fastapi_app",
    "format_telemetry_event",
    "get_genai_client",
    "is_safe_input",
    "root_agent",
]
