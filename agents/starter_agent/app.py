# Copyright 2026 Google LLC
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

"""Starter Agent implementation using Google GenAI SDK and FastAPI."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")

app = FastAPI(
    title="Starter Agent Service",
    description="Production-grade agent blueprint using Google GenAI SDK",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    query: str = Field(..., description="User prompt or inquiry.")
    session_id: str | None = Field(default=None, description="Optional tracking session ID.")
    user_context: dict[str, Any] | None = Field(
        default_factory=dict, description="Metadata and context attributes."
    )


class QueryResponse(BaseModel):
    response: str = Field(..., description="Generated text response.")
    latency_ms: float = Field(..., description="Execution latency in milliseconds.")
    model_version: str = Field(..., description="Model identifier used for generation.")
    session_id: str | None = Field(default=None, description="Session tracking ID.")


def get_genai_client() -> genai.Client:
    """Initializes Google GenAI client configured with Vertex AI backend."""
    return genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location=GCP_REGION,
    )


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Liveness and readiness health probe."""
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest) -> QueryResponse:
    """Processes user queries via Google GenAI SDK."""
    start_time = time.time()
    try:
        client = get_genai_client()
        system_instruction = (
            "You are a helpful, enterprise-grade AI assistant. "
            "Provide accurate, concise, and structured answers."
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=request.query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )

        duration_ms = (time.time() - start_time) * 1000.0
        generated_text = response.text or ""

        return QueryResponse(
            response=generated_text,
            latency_ms=round(duration_ms, 2),
            model_version=MODEL_NAME,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error(f"Error generating agent response: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
