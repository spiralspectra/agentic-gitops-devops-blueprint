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

"""Unit tests verifying Cloud Monitoring SRE layer, 28-day SLOs, and alert runbooks."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_DIR = REPO_ROOT / "deployment" / "terraform" / "single-project"
RUNBOOK_PATH = REPO_ROOT / "docs" / "RUNBOOK_ALERTS.md"


def test_deployer_has_monitoring_admin_and_metric_writer_roles() -> None:
    variables_tf = (TF_DIR / "variables.tf").read_text(encoding="utf-8")
    deployer_block = re.search(
        r'variable "deployer_project_roles" \{(.*?)\n\}',
        variables_tf,
        re.S,
    )
    assert deployer_block is not None
    roles = deployer_block.group(1)
    assert '"roles/monitoring.admin"' in roles
    assert '"roles/monitoring.metricWriter"' in roles


def test_monitoring_tf_defines_notification_channel_and_log_metrics() -> None:
    monitoring_tf = (TF_DIR / "monitoring.tf").read_text(encoding="utf-8")

    # Notification channel
    assert 'resource "google_monitoring_notification_channel" "email"' in monitoring_tf

    # Log metrics for errors and guardrails
    log_metrics = re.findall(r'resource "google_logging_metric" "([a-z0-9_]+)"', monitoring_tf)
    assert "tool_execution_errors" in log_metrics
    assert "guardrail_refusals" in log_metrics


def test_monitoring_tf_configures_28_day_rolling_slos() -> None:
    monitoring_tf = (TF_DIR / "monitoring.tf").read_text(encoding="utf-8")

    # Custom service
    assert 'resource "google_monitoring_custom_service" "agent_service"' in monitoring_tf

    # SLO targets
    slos = re.findall(r'resource "google_monitoring_slo" "([a-z0-9_]+)"', monitoring_tf)
    assert set(slos) == {"availability_slo", "latency_slo"}

    # Rolling window is 28 days
    assert monitoring_tf.count("rolling_period_days = 28") == 2
    assert "goal         = 0.995" in monitoring_tf
    assert "goal         = 0.95" in monitoring_tf


def test_monitoring_tf_configures_fast_and_slow_burn_alerts_with_runbooks() -> None:
    monitoring_tf = (TF_DIR / "monitoring.tf").read_text(encoding="utf-8")

    policies = re.findall(
        r'resource "google_monitoring_alert_policy" "([a-z0-9_]+)"', monitoring_tf
    )
    assert "fast_burn_availability" in policies
    assert "slow_burn_availability" in policies

    # Auto close configured
    assert monitoring_tf.count("auto_close =") >= len(policies)

    # Runbook linkage
    assert "${local.runbook_base_url}#" in monitoring_tf


def test_monitoring_tf_configures_uptime_check() -> None:
    monitoring_tf = (TF_DIR / "monitoring.tf").read_text(encoding="utf-8")
    assert 'resource "google_monitoring_uptime_check_config" "agent_health_check"' in monitoring_tf
    assert 'path         = "/healthz"' in monitoring_tf


def test_runbook_alerts_documents_required_sections() -> None:
    assert RUNBOOK_PATH.is_file(), f"{RUNBOOK_PATH} must exist"
    text = RUNBOOK_PATH.read_text(encoding="utf-8")

    for section in (
        "## Alert: Fast Burn Availability",
        "## Alert: Slow Burn Availability",
        "## Alert: High Latency",
        "### Metadata",
        "### Triage Queries",
        "### Mitigation",
    ):
        assert section in text, f"Missing runbook section: {section}"
