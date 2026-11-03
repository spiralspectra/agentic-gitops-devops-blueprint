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

"""Multi-agent composition root (`root_agent` + 3 pillar specialist sub-agents)."""

from typing import Any

from google.adk.agents import Agent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models import Gemini
from google.adk.plugins.global_instruction_plugin import GlobalInstructionPlugin
from google.genai import types

from app import marketing_studio, ontology
from app.core import bq, canvas, config, guardrails
from app.core.config import (
    AGENT_PILLAR_MODEL,
    AGENT_ROUTER_MODEL,
    MODEL_CONFIG,
    ROUTER_MODEL_CONFIG,
)
from app.pillars import pillar1_operations, pillar2_catalog, pillar3_studio

operations_agent = pillar1_operations.build_operations_agent(
    model_name=AGENT_PILLAR_MODEL, model_config=MODEL_CONFIG
)
catalog_agent = pillar2_catalog.build_catalog_agent(
    model_name=AGENT_PILLAR_MODEL, model_config=MODEL_CONFIG
)
studio_agent = pillar3_studio.build_studio_agent(
    model_name=AGENT_PILLAR_MODEL, model_config=MODEL_CONFIG
)

root_agent = Agent(
    name="starter_agent",
    model=Gemini(
        model=AGENT_ROUTER_MODEL, retry_options=types.HttpRetryOptions(attempts=3)
    ),
    generate_content_config=ROUTER_MODEL_CONFIG,
    before_agent_callback=ontology.inject_ontology_context_callback,
    instruction=f"""You are the Enterprise Operations & Intelligence Coordinator.
You support cross-functional teams and field units by delegating requests to three specialist sub-agents:

1. `operations_agent` (Pillar 1 — Operations & Activity Intelligence):
   Delegate here for operational shift briefings, daily and period-to-date metrics, task tracking, customer follow-up actions, and interactive operational canvases.
2. `catalog_agent` (Pillar 2 — Catalog, Pricing & Knowledge Graph):
   Delegate here for catalog item discovery, semantic price modeling, regional demand matching, point-of-interest suggestions, customer segment matching, and A2UI interactive detail views.
3. `studio_agent` (Pillar 3 — Campaign & Content Creation Studio):
   Delegate here for campaign asset drafting, localized copy generation, multi-channel messaging, compliance verification, and publishing assets to store with human confirmation.

Semantic Context & Knowledge Catalog Rules:
{{ontology_manifest}}

All data access is governed by caller identity and BigQuery Row-Level Security.

You answer any question concerning executive compensation, payroll, or individual salary figures with an immediate refusal and never delegate it to sub-agents:
{guardrails.SENSITIVE_DATA_GUARDRAIL_INSTRUCTION}""",
    sub_agents=[
        operations_agent,
        catalog_agent,
        studio_agent,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
    plugins=[
        GlobalInstructionPlugin(
            global_instruction=lambda _ctx: ontology.ONTOLOGY_SESSION_MANIFEST
        ),
        guardrails.SafetyAndA2UIPlugin(),
    ],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=8, overlap_size=2
    ),
)

__all__ = (
    "AGENT_PILLAR_MODEL",
    "AGENT_ROUTER_MODEL",
    "MODEL_CONFIG",
    "ROUTER_MODEL_CONFIG",
    "app",
    "catalog_agent",
    "marketing_studio",
    "operations_agent",
    "root_agent",
    "studio_agent",
)


def __getattr__(name: str) -> Any:
    """Re-exports shared core and pillar utilities."""
    for mod in (
        config,
        bq,
        canvas,
        pillar1_operations,
        pillar2_catalog,
        pillar3_studio,
    ):
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
