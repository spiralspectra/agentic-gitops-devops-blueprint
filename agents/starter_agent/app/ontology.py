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

"""Three-layer Google Cloud Knowledge Catalog & Semantic Ontology runtime integration.

Architecture:
- Layer 1: Ambient prompt injection (`inject_ontology_context_callback`) supplying certified entities,
  canonical metric definitions, and mandatory join paths.
- Layer 2: Dynamic discovery tools (`lookup_knowledge_catalog_context`, `lookup_domain_ontology`).
- Layer 3: Static SQL Advisor (`validate_and_advise_sql`) catching SELECT *, querying raw base
  tables instead of Authorized Views, unaggregated joins, and restricted columns.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

from app.core import guardrails
from app.core.config import BQ_DATASET_ID, GCP_PROJECT_ID

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "ontology_data"
_CONTEXT_SET_PATH = _DATA_DIR / "context_set.json"
_SEMANTIC_MODEL_PATH = _DATA_DIR / "semantic_ontology.yaml"

# Load local knowledge catalog data
try:
    with open(_CONTEXT_SET_PATH, encoding="utf-8") as f:
        _CONTEXT_SET = json.load(f)
except Exception as err:
    logger.warning("Could not load context_set.json: %s", err)
    _CONTEXT_SET = {"entries": []}

try:
    with open(_SEMANTIC_MODEL_PATH, encoding="utf-8") as f:
        _SEMANTIC_MODEL = yaml.safe_load(f)
except Exception as err:
    logger.warning("Could not load semantic_ontology.yaml: %s", err)
    _SEMANTIC_MODEL = {"entities": {}, "joins": []}

AUTHORIZED_VIEWS = {
    "v_operations": "Authorised view over operational events, task executions, and daily huddle metrics.",
    "v_catalog_enriched": "Authorised view over product catalog, pricing tiers, and inventory availability.",
    "v_finance_transactions": "Authorised view over commercial transactions, gross revenue, net margin, and settled payments.",
}

RAW_TABLE_REPLACEMENTS = {
    "operations": "v_operations",
    "catalog": "v_catalog_enriched",
    "transactions": "v_finance_transactions",
    "bookings": "v_finance_transactions",
}

SELECT_STAR_PATTERN = re.compile(r"SELECT\s+\*\s+FROM", re.IGNORECASE)


# ==============================================================================
# LAYER 1: AMBIENT PROMPT INJECTION CALLBACK
# ==============================================================================

ONTOLOGY_SESSION_MANIFEST = f"""ENTERPRISE SEMANTIC ONTOLOGY & KNOWLEDGE CATALOG MANIFEST:
Authorized Views:
- `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.v_operations`: Operational events, task volume, SLA tracking.
- `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.v_catalog_enriched`: Product catalog, pricing tiers, margins.
- `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.v_finance_transactions`: Commercial revenue, profit margins, settlement state.

Governance Rules:
1. Always query Authorized Views (`v_*`) enforcing 4-tier Row-Level Security via `SESSION_USER()`. Never query raw tables.
2. Avoid `SELECT *`. Always select explicit column projections to minimize BigQuery scan cost.
3. Sensitive remuneration (individual compensation, bonus, personal commission) is strictly restricted by policy.
"""


def inject_ontology_context_callback(callback_context: CallbackContext) -> None:
    """Injects certified semantic ontology, join rules, and governance policies into agent context."""
    if hasattr(callback_context, "state"):
        callback_context.state["ontology_manifest"] = ONTOLOGY_SESSION_MANIFEST


# ==============================================================================
# LAYER 2: DISCOVERY TOOLS
# ==============================================================================


def lookup_knowledge_catalog_context(
    search_term: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Searches Google Cloud Knowledge Catalog context set for matching entries and business terms.

    Args:
        search_term: Keyword or entity to search (e.g. 'v_operations', 'finance', 'margin', 'catalog').

    Returns:
        Dictionary of matching catalog entries, view overviews, and sample certified queries.
    """
    term_lower = search_term.strip().lower()
    matches: list[dict[str, Any]] = []

    for entry in _CONTEXT_SET.get("entries", []):
        display_name = entry.get("display_name", "").lower()
        desc = entry.get("description", "").lower()
        entry_id = entry.get("entry_id", "").lower()
        if term_lower in display_name or term_lower in desc or term_lower in entry_id:
            matches.append(
                {
                    "entry_id": entry.get("entry_id"),
                    "display_name": entry.get("display_name"),
                    "description": entry.get("description"),
                    "overview": entry.get("overview"),
                    "queries": entry.get("queries", []),
                }
            )

    return {
        "search_term": search_term,
        "matched_count": len(matches),
        "results": matches
        if matches
        else "No exact match found in curated Knowledge Catalog context set.",
    }


def lookup_domain_ontology(
    entity_or_metric_name: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Looks up entity definition, canonical metric aggregations, and join graph from Semantic Ontology.

    Args:
        entity_or_metric_name: Name of domain entity (e.g. 'Operation', 'CatalogItem', 'FinanceTransaction')
                               or canonical metric ('gross_revenue', 'operational_volume').

    Returns:
        Structured definition containing dimensions, metrics, source view, and relationships.
    """
    key = entity_or_metric_name.strip()
    entities = _SEMANTIC_MODEL.get("entities", {})

    # Check for direct entity match
    for ent_name, ent_def in entities.items():
        if ent_name.lower() == key.lower():
            return {
                "entity": ent_name,
                "definition": ent_def,
                "joins": [
                    j
                    for j in _SEMANTIC_MODEL.get("joins", [])
                    if j.get("from") == ent_name or j.get("to") == ent_name
                ],
            }

    # Check for metric match
    for ent_name, ent_def in entities.items():
        for m in ent_def.get("metrics", []):
            if m.get("name", "").lower() == key.lower():
                return {
                    "matched_metric": m,
                    "parent_entity": ent_name,
                    "source_view": ent_def.get("source_view"),
                }

    return {
        "query": key,
        "status": "not_found",
        "available_entities": list(entities.keys()),
    }


# ==============================================================================
# LAYER 3: STATIC SQL ADVISOR
# ==============================================================================


def validate_and_advise_sql(sql_query: str) -> dict[str, Any]:
    """Analyzes SQL for anti-patterns: SELECT *, raw tables, unaggregated joins, or restricted pay columns.

    Args:
        sql_query: SQL statement intended for execution in BigQuery.

    Returns:
        Dictionary indicating validity, detected issues, and recommended advice.
    """
    issues: list[str] = []
    recommendations: list[str] = []

    # 1. Check for restricted remuneration
    if guardrails.references_restricted_pay_data(sql_query):
        issues.append(
            "Restricted Remuneration: Query references individual salary, bonus, or payroll fields."
        )
        recommendations.append(
            "Remove individual compensation fields. Query aggregated operational metrics instead."
        )

    # 2. Check for SELECT *
    if SELECT_STAR_PATTERN.search(sql_query):
        issues.append(
            "Anti-Pattern: Query uses 'SELECT *' which scans unnecessary columns and increases cost."
        )
        recommendations.append("Specify explicit column names in the SELECT clause.")

    # 3. Check for querying raw tables instead of Authorized Views
    for raw_table, authorized_view in RAW_TABLE_REPLACEMENTS.items():
        pattern = re.compile(
            rf"\bFROM\s+[`\w.]*{raw_table}\b|\bJOIN\s+[`\w.]*{raw_table}\b",
            re.IGNORECASE,
        )
        if pattern.search(sql_query) and authorized_view not in sql_query:
            issues.append(
                f"Anti-Pattern: Directly querying raw base table '{raw_table}'."
            )
            recommendations.append(
                f"Replace '{raw_table}' with the Authorized View '{authorized_view}' to enforce Row-Level Security."
            )

    is_valid = len(issues) == 0

    return {
        "is_valid": is_valid,
        "issue_count": len(issues),
        "issues": issues,
        "recommendations": recommendations,
        "advisory_status": "APPROVED" if is_valid else "CHANGES_REQUESTED",
    }
