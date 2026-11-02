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

"""Unit tests for CI terraform guard scripts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deployment.ci import check_engine_consistency, guard_terraform_plan


def test_guard_allows_non_destructive_plan(tmp_path: Path):
    plan = {
        "resource_changes": [
            {
                "address": "google_storage_bucket.app",
                "type": "google_storage_bucket",
                "change": {"actions": ["create"]},
            },
            {
                "address": 'google_project_service.services["run.googleapis.com"]',
                "type": "google_project_service",
                "change": {"actions": ["no-op"]},
            },
            {
                "address": "google_monitoring_alert_policy.fast_burn",
                "type": "google_monitoring_alert_policy",
                "change": {"actions": ["update"]},
            },
        ]
    }
    assert guard_terraform_plan.destructive_changes(plan) == []

    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    assert guard_terraform_plan.main(["guard_terraform_plan.py", str(plan_file)]) == 0


def test_guard_allows_safe_iam_member_tightening():
    plan = {
        "resource_changes": [
            {
                "address": "google_project_iam_member.stale_reader",
                "type": "google_project_iam_member",
                "name": "stale_reader",
                "change": {"actions": ["delete"]},
            },
            {
                "address": "google_bigquery_table_iam_member.old_binding",
                "type": "google_bigquery_table_iam_member",
                "name": "old_binding",
                "change": {"actions": ["create", "delete"]},
            },
        ]
    }
    assert guard_terraform_plan.destructive_changes(plan) == []


def test_guard_blocks_stateful_resource_deletion():
    plan = {
        "resource_changes": [
            {
                "address": "google_storage_bucket.logs",
                "type": "google_storage_bucket",
                "name": "logs",
                "change": {"actions": ["delete"]},
            },
            {
                "address": "google_vertex_ai_reasoning_engine.app[0]",
                "type": "google_vertex_ai_reasoning_engine",
                "name": "app",
                "change": {"actions": ["delete"]},
            },
        ]
    }
    destructive = guard_terraform_plan.destructive_changes(plan)
    assert len(destructive) == 2
    assert destructive[0][0] == "google_storage_bucket.logs"
    assert destructive[1][0] == "google_vertex_ai_reasoning_engine.app[0]"


def test_guard_blocks_protected_pipeline_iam_deletion():
    plan = {
        "resource_changes": [
            {
                "address": "google_project_iam_member.deployer",
                "type": "google_project_iam_member",
                "name": "deployer",
                "change": {"actions": ["delete"]},
            }
        ]
    }
    destructive = guard_terraform_plan.destructive_changes(plan)
    assert len(destructive) == 1
    assert destructive[0][0] == "google_project_iam_member.deployer"


def test_guard_allows_destruction_when_env_var_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    plan = {
        "resource_changes": [
            {
                "address": "google_storage_bucket.temp",
                "type": "google_storage_bucket",
                "name": "temp",
                "change": {"actions": ["delete"]},
            }
        ]
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")

    # Without override, returns 1
    monkeypatch.delenv("TF_ALLOW_DESTROY", raising=False)
    assert guard_terraform_plan.main(["guard_terraform_plan.py", str(plan_file)]) == 1

    # With override, returns 0
    monkeypatch.setenv("TF_ALLOW_DESTROY", "true")
    assert guard_terraform_plan.main(["guard_terraform_plan.py", str(plan_file)]) == 0


def test_engine_consistency_matches(tmp_path: Path):
    tfvars = tmp_path / "env.tfvars"
    tfvars.write_text('reasoning_engine_id = "1234567890123456789"\n', encoding="utf-8")

    metadata = tmp_path / "deployment_metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "remote_agent_runtime_id": (
                    "projects/123/locations/us-central1/reasoningEngines/1234567890123456789"
                )
            }
        ),
        encoding="utf-8",
    )

    rc = check_engine_consistency.main(
        [
            "--tfvars",
            str(tfvars),
            "--metadata",
            str(metadata),
            "--state-engine",
            "projects/123/locations/us-central1/reasoningEngines/1234567890123456789",
        ]
    )
    assert rc == 0


def test_engine_consistency_detects_mismatch(tmp_path: Path):
    tfvars = tmp_path / "env.tfvars"
    tfvars.write_text('reasoning_engine_id = "1111111111111111111"\n', encoding="utf-8")

    metadata = tmp_path / "deployment_metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "remote_agent_runtime_id": (
                    "projects/123/locations/us-central1/reasoningEngines/2222222222222222222"
                )
            }
        ),
        encoding="utf-8",
    )

    rc = check_engine_consistency.main(["--tfvars", str(tfvars), "--metadata", str(metadata)])
    assert rc == 1
