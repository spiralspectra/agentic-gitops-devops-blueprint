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

"""Unit tests for Semantic Ontology and Knowledge Catalog runtime integration."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ontology import (
    inject_ontology_context_callback,
    lookup_domain_ontology,
    lookup_knowledge_catalog_context,
    validate_and_advise_sql,
)


def test_layer1_prompt_injection_callback():
    mock_cb_context = MagicMock()
    mock_cb_context.state = {}

    inject_ontology_context_callback(mock_cb_context)

    assert "ontology_manifest" in mock_cb_context.state
    manifest = mock_cb_context.state["ontology_manifest"]
    assert "ENTERPRISE SEMANTIC ONTOLOGY" in manifest
    assert "v_operations" in manifest
    assert "v_catalog_enriched" in manifest
    assert "v_finance_transactions" in manifest
    assert "SESSION_USER()" in manifest


def test_layer2_knowledge_catalog_context_lookup():
    res = lookup_knowledge_catalog_context("operations")
    assert res["search_term"] == "operations"
    # Even if empty or populated, it should return a structured dict
    assert "results" in res
    assert "matched_count" in res


def test_layer2_domain_ontology_lookup():
    res = lookup_domain_ontology("gross_revenue")
    assert "query" in res or "matched_metric" in res or "entity" in res


def test_layer3_sql_advisor_allows_clean_authorized_view_query():
    clean_sql = """
        SELECT
            transaction_id,
            transaction_date,
            gross_sales_amount
        FROM `enterprise-project.analytics.v_finance_transactions`
        WHERE is_cancelled = FALSE
    """
    advisor = validate_and_advise_sql(clean_sql)
    assert advisor["is_valid"] is True
    assert advisor["advisory_status"] == "APPROVED"
    assert advisor["issue_count"] == 0


def test_layer3_sql_advisor_flags_select_star():
    bad_sql = "SELECT * FROM `enterprise-project.analytics.v_operations`"
    advisor = validate_and_advise_sql(bad_sql)
    assert advisor["is_valid"] is False
    assert advisor["advisory_status"] == "CHANGES_REQUESTED"
    assert any("SELECT *" in issue for issue in advisor["issues"])


def test_layer3_sql_advisor_flags_raw_table_queries():
    for raw_tbl, view_tbl in [("operations", "v_operations"), ("catalog", "v_catalog_enriched")]:
        bad_sql = f"SELECT id, name FROM {raw_tbl} WHERE active = TRUE"
        advisor = validate_and_advise_sql(bad_sql)
        assert advisor["is_valid"] is False
        assert any(f"raw base table '{raw_tbl}'" in issue for issue in advisor["issues"])
        assert any(view_tbl in rec for rec in advisor["recommendations"])


def test_layer3_sql_advisor_flags_restricted_remuneration():
    bad_sql = "SELECT employee_id, individual_salary, annual_bonus FROM `analytics.v_hr_records`"
    advisor = validate_and_advise_sql(bad_sql)
    assert advisor["is_valid"] is False
    assert any("Restricted Remuneration" in issue for issue in advisor["issues"])
