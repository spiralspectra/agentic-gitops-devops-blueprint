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

"""Static security and observability configuration tests."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cicd_identity_locks_deployer_to_main_branch():
    cicd_tf = (
        REPO_ROOT / "deployment" / "terraform" / "single-project" / "cicd_identity.tf"
    ).read_text(encoding="utf-8")

    # Must map attribute.ref
    assert '"attribute.ref"' in cicd_tf
    # Must specify principalSet strictly to refs/heads/main
    assert "attribute.ref/refs/heads/main" in cicd_tf
    # Deployer service account must bind to principal_set_main
    assert 'resource "google_service_account_iam_member" "deployer_wif_user"' in cicd_tf
    assert "member             = local.principal_set_main" in cicd_tf


def test_agent_runtime_prevents_accidental_destroy():
    runtime_tf = (
        REPO_ROOT / "deployment" / "terraform" / "single-project" / "agent_runtime.tf"
    ).read_text(encoding="utf-8")

    assert 'resource "google_vertex_ai_reasoning_engine" "app"' in runtime_tf
    assert "prevent_destroy = true" in runtime_tf
    assert "ignore_changes" in runtime_tf
    assert "spec," in runtime_tf


def test_monitoring_defines_slos_and_runbook_alerts():
    monitoring_tf = (
        REPO_ROOT / "deployment" / "terraform" / "single-project" / "monitoring.tf"
    ).read_text(encoding="utf-8")

    # 28-day rolling SLOs
    assert "rolling_period_days = 28" in monitoring_tf
    assert "0.995" in monitoring_tf  # 99.5% availability target

    # Burn rate alert policies
    assert "google_monitoring_alert_policy" in monitoring_tf
    assert "fast_burn" in monitoring_tf
    assert "slow_burn" in monitoring_tf

    # Runbook alert documentation links
    assert "docs/RUNBOOK_ALERTS.md" in monitoring_tf


def test_authorized_view_enforces_zero_trust_row_level_security():
    view_sql = (REPO_ROOT / "data" / "views" / "10_v_authorized_records.sql").read_text(
        encoding="utf-8"
    )

    # Session user extraction and normalization
    assert "SESSION_USER()" in view_sql
    assert "LOWER(TRIM(SESSION_USER()))" in view_sql
    assert "NULLIF" in view_sql

    # Zero-trust row-level security condition
    assert "WHERE EXISTS" in view_sql
