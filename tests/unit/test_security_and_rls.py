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

"""Unit tests for 4-tier Row-Level Security, caller token isolation, and remuneration guardrails."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.core import bq
from app.core.guardrails import (
    RestrictedPayDataError,
    assert_no_restricted_pay_data,
    redact_restricted_pay_fields,
    references_restricted_pay_data,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeToolContext:
    def __init__(self, state_dict: dict[str, Any] | None = None) -> None:
        self.state = state_dict or {}

    def get_auth_response(self, auth_config: Any) -> Any:
        return None


def test_four_tier_rls_sql_view_invariants():
    view_path = REPO_ROOT / "data" / "views" / "10_v_authorized_records.sql"
    assert view_path.exists(), f"{view_path} must exist"
    sql = view_path.read_text(encoding="utf-8")

    # Tier 1: Strict normalization
    assert "LOWER(TRIM(SESSION_USER()))" in sql

    # Tier 2: Blank string protection
    assert "NULLIF(TRIM(" in sql

    # Tier 3: Fan-out prevention via WHERE EXISTS
    assert "WHERE" in sql
    assert "EXISTS" in sql
    import re

    clean_sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    assert "INNER JOIN" not in clean_sql.upper()

    # Tier 4: Column Projection - sensitive credentials excluded
    assert "password" not in sql.lower()
    assert "secret" not in sql.lower()


def test_per_caller_oauth_isolation():
    ctx_user1 = _FakeToolContext({"enterprise-bigquery-oauth": "token-alice-123"})
    ctx_user2 = _FakeToolContext({"enterprise-bigquery-oauth": "token-bob-456"})

    created_clients = []

    def mock_bq_client(*args, **kwargs):
        client = MagicMock()
        client.credentials = kwargs.get("credentials")
        created_clients.append(client)
        return client

    with patch("app.core.bq.bigquery.Client", side_effect=mock_bq_client):
        c1 = bq.get_caller_bq_client(ctx_user1)
        c2 = bq.get_caller_bq_client(ctx_user2)

    assert c1 is not c2
    assert c1.credentials.token == "token-alice-123"
    assert c2.credentials.token == "token-bob-456"


def test_deployed_runtime_fails_closed_when_anonymous(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", "engine-12345")
    ctx_anon = _FakeToolContext({})

    with pytest.raises(PermissionError, match="Per-user caller identity is required"):
        bq.get_caller_bq_client(ctx_anon)


def test_remuneration_pre_query_guardrail_blocks_restricted_sql():
    blocked_queries = [
        "SELECT individual_salary FROM `data.payroll`",
        "SELECT bonus_amount FROM `data.employee_bonuses`",
        "SELECT worker_id, take_home, hourly_rate FROM `data.wages`",
        "SELECT ssn, bank_account FROM `data.sensitive_pii`",
    ]
    for q in blocked_queries:
        assert references_restricted_pay_data(q) is True
        with pytest.raises(RestrictedPayDataError):
            assert_no_restricted_pay_data(q)


def test_remuneration_allowed_aggregates_pass():
    allowed_queries = [
        "SELECT department_code, headcount, total_fte FROM `data.departments`",
        "SELECT avg_team_size, staff_count FROM `data.operations`",
        "SELECT item_id, decommission_status FROM `data.assets`",
    ]
    for q in allowed_queries:
        assert references_restricted_pay_data(q) is False
        assert_no_restricted_pay_data(q)  # Should not raise


def test_post_query_payload_redaction():
    raw_payload = {
        "event_id": "EVT-100",
        "department": "Engineering",
        "individual_salary": 125000,
        "bonus_amount": 15000,
        "staff_details": [
            {"name": "Alice", "hourly_rate": 65.0, "role": "Architect"},
            {"name": "Bob", "bank_account": "12345678", "role": "Engineer"},
        ],
    }

    sanitized = redact_restricted_pay_fields(raw_payload)

    assert sanitized["event_id"] == "EVT-100"
    assert sanitized["department"] == "Engineering"
    assert sanitized["individual_salary"] == "[REDACTED_BY_POLICY]"
    assert sanitized["bonus_amount"] == "[REDACTED_BY_POLICY]"
    assert sanitized["staff_details"][0]["hourly_rate"] == "[REDACTED_BY_POLICY]"
    assert sanitized["staff_details"][0]["role"] == "Architect"
    assert sanitized["staff_details"][1]["bank_account"] == "[REDACTED_BY_POLICY]"
