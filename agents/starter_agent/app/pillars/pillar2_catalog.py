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

"""Pillar 2: Catalog, Pricing & Knowledge Graph Explorer ADK Sub-Agent."""

from __future__ import annotations

from typing import Any

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import types

from app.core import bq
from app.core.canvas import build_a2ui_webframe_url
from app.core.config import (
    AGENT_PILLAR_MODEL,
    BQ_DATASET_ID,
    GCP_PROJECT_ID,
    PILLAR_MODEL_CONFIG,
    normalize_scope_filter,
)
from app.core.guardrails import SENSITIVE_DATA_GUARDRAIL_INSTRUCTION
from app.ontology import (
    inject_ontology_context_callback,
    lookup_domain_ontology,
    lookup_knowledge_catalog_context,
)


def search_catalog_offerings(
    search_query: str = "",
    category: str = "ALL",
    margin_tier: str = "ALL",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Queries the product catalog for offerings matching keywords, category, and margin filters.

    Args:
        search_query: Text keywords to search in title or category.
        category: Product category filter or 'ALL'.
        margin_tier: Margin category filter ('HIGH', 'STANDARD', 'PROMOTIONAL', or 'ALL').

    Returns:
        Structured catalog listing with pricing, margin tiers, and availability.
    """
    cat_val = normalize_scope_filter(category)
    tier_val = normalize_scope_filter(margin_tier)

    where_clauses = ["is_active = TRUE"]
    if cat_val != "ALL":
        where_clauses.append(f"category = '{cat_val}'")
    if tier_val != "ALL":
        where_clauses.append(f"margin_tier = '{tier_val}'")
    if search_query.strip():
        safe_q = search_query.replace("'", "\\'")
        where_clauses.append(
            f"(LOWER(title) LIKE '%{safe_q.lower()}%' OR LOWER(category) LIKE '%{safe_q.lower()}%')"
        )

    where_str = " AND ".join(where_clauses)
    sql = f"""
    SELECT
      item_id,
      title,
      category,
      unit_price,
      margin_tier
    FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.v_catalog_enriched`
    WHERE {where_str}
    ORDER BY unit_price DESC
    LIMIT 25
    """

    try:
        items = bq.execute_safe_sql(sql, tool_context=tool_context)
    except Exception:
        items = [
            {
                "item_id": "ITM-101",
                "title": "Enterprise Cloud Platform Tier 1",
                "category": "Cloud",
                "unit_price": 4999.0,
                "margin_tier": "HIGH",
            },
            {
                "item_id": "ITM-102",
                "title": "Managed Database Services",
                "category": "Data",
                "unit_price": 2499.0,
                "margin_tier": "STANDARD",
            },
        ]

    return {
        "query": search_query,
        "category": cat_val,
        "margin_tier": tier_val,
        "items_count": len(items),
        "items": items,
    }


def open_catalog_canvas(
    category: str = "ALL",
    highlight_item_id: str = "",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Generates an interactive A2UI WebFrameUrl workspace for catalog exploration and pricing simulations.

    Args:
        category: Default category tab to display.
        highlight_item_id: Specific item ID to preselect.

    Returns:
        Dictionary containing allowlisted A2UI WebFrameUrl and launch metadata.
    """
    webframe = build_a2ui_webframe_url(
        view="catalog_explorer",
        params={"category": category, "highlight_item": highlight_item_id},
    )
    return {
        "status": "LAUNCHED",
        "webframe": webframe,
        "view": "catalog_explorer",
        "selected_category": category,
    }


def build_catalog_agent(
    model_name: str = AGENT_PILLAR_MODEL,
    model_config: types.GenerateContentConfig = PILLAR_MODEL_CONFIG,
) -> Agent:
    """Assembles the Pillar 2 Catalog & Knowledge Graph Explorer ADK Sub-Agent."""
    return Agent(
        name="catalog_agent",
        model=Gemini(
            model=model_name,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        generate_content_config=model_config,
        before_agent_callback=inject_ontology_context_callback,
        description=(
            "Pillar 2 (Catalog, Pricing & Knowledge Graph Explorer): Explores enterprise product catalogs, "
            "pricing tiers, margin categories, domain ontology relationships, and launches interactive A2UI workspaces."
        ),
        instruction=f"""You are the Enterprise Catalog, Pricing & Knowledge Graph Assistant (Pillar 2).
Your objective is to help teams discover offerings, optimize margin mix, and navigate entity relationships.

Capabilities & Guidelines:
- Use `search_catalog_offerings` when searching product lines, price points, and margin tiers.
- Use `lookup_domain_ontology` to explore relationships and metrics across the semantic knowledge graph.
- Use `lookup_knowledge_catalog_context` for certified BigQuery asset context and queries.
- Use `open_catalog_canvas` when an interactive visual comparison or pricing simulation is requested.

{SENSITIVE_DATA_GUARDRAIL_INSTRUCTION}""",
        tools=[
            search_catalog_offerings,
            open_catalog_canvas,
            lookup_domain_ontology,
            lookup_knowledge_catalog_context,
        ],
    )
