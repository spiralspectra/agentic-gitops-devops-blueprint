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

"""Pillar 3: Compliance-Gated Campaign & Artifact Studio ADK Sub-Agent."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.core.config import AGENT_PILLAR_MODEL, PILLAR_MODEL_CONFIG
from app.core.guardrails import SENSITIVE_DATA_GUARDRAIL_INSTRUCTION
from app.marketing_studio import (
    draft_campaign_asset,
    file_campaign_to_store,
    validate_copy_compliance,
)
from app.ontology import inject_ontology_context_callback


def build_studio_agent(
    model_name: str = AGENT_PILLAR_MODEL,
    model_config: types.GenerateContentConfig = PILLAR_MODEL_CONFIG,
) -> Agent:
    """Assembles the Pillar 3 Compliance-Gated Campaign & Artifact Studio ADK Sub-Agent."""
    return Agent(
        name="studio_agent",
        model=Gemini(
            model=model_name,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        generate_content_config=model_config,
        before_agent_callback=inject_ontology_context_callback,
        description=(
            "Pillar 3 (Campaign & Artifact Studio): Generates marketing and communication assets, "
            "evaluates brand and regulatory compliance, and enforces human-in-the-loop approval before store persistence."
        ),
        instruction=f"""You are the Enterprise Campaign & Artifact Studio Assistant (Pillar 3).
Your role is to assist in drafting, validating, and publishing compliant promotional and operational content.

Strict Operational Guidelines:
1. When generating new collateral, invoke `draft_campaign_asset`.
2. When evaluating copy provided by the user, invoke `validate_copy_compliance`.
3. HUMAN-IN-THE-LOOP COMMIT RULE:
   - To store or commit an asset to the permanent store, call `file_campaign_to_store`.
   - Never call `file_campaign_to_store` with `confirmed=True` unless the human operator has explicitly verified and approved the copy.
   - If the operator has not explicitly confirmed, call with `confirmed=False` or present the draft and ask for their confirmation first.

{SENSITIVE_DATA_GUARDRAIL_INSTRUCTION}""",
        tools=[
            draft_campaign_asset,
            validate_copy_compliance,
            file_campaign_to_store,
        ],
    )
