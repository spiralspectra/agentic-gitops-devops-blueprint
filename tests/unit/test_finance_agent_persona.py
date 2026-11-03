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

"""Unit tests for the Corporate Finance & FP&A agent persona spec (finance-agent/).

Runs offline without network access: compiles the declarative persona using
finance-agent/sync_finance_agent_persona.py and verifies all invariants required
by the AnalystAgentPersona API and skill execution.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FINANCE_AGENT_DIR = REPO_ROOT / "finance-agent"
VIEWS_DIR = REPO_ROOT / "deployment" / "data" / "views"
PROJECT = "your-gcp-project-id"
DATASET = "enterprise_lakehouse"

_spec = importlib.util.spec_from_file_location(
    "sync_finance_agent_persona", FINANCE_AGENT_DIR / "sync_finance_agent_persona.py"
)
sync = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sync)


@pytest.fixture(scope="module")
def compiled() -> tuple[str, dict]:
    return sync.compile_persona(FINANCE_AGENT_DIR / "personas" / "default.json", PROJECT, "global")


def _resource_table_names(body: dict) -> set[str]:
    names = set()
    for res in body["resources"]:
        target = res["bigqueryResource"].get("bigqueryTable") or res["bigqueryResource"].get(
            "bigqueryDataset"
        )
        names.add(target.rsplit("/", 1)[-1])
    return names


def test_persona_is_the_gemini_enterprise_entry_persona(
    compiled: tuple[str, dict],
) -> None:
    persona_id, body = compiled
    assert persona_id == "default"
    assert body["name"] == f"projects/{PROJECT}/locations/global/analystAgentPersonas/default"
    assert body["role"] == "ANALYST_ROLE_CORPORATE_FINANCE_ANALYST"
    assert body["displayName"]


def test_model_description_carries_the_house_rules(compiled: tuple[str, dict]) -> None:
    _, body = compiled
    text = body["modelDescription"]
    for must in (
        "is_cancelled",
        "gross_sales_amount",
        "margin_amount",
        "v_finance_transactions",
        "v_finance_receipts",
        "Row-Level Security",
    ):
        assert must in text, f"modelDescription must mention {must!r}"


def test_resources_are_finance_views_in_the_shared_dataset_without_pii(
    compiled: tuple[str, dict],
) -> None:
    _, body = compiled
    names = _resource_table_names(body)
    assert {
        "v_finance_transactions",
        "v_finance_receipts",
        "v_finance_customer_bridge",
    } <= names

    # Sensitive / PII master tables must never be exposed to the finance persona
    assert "user_credentials" not in names
    assert "customermaster" not in names
    assert "user_entitlements" not in names

    for res in body["resources"]:
        target = res["bigqueryResource"].get("bigqueryTable") or res["bigqueryResource"].get(
            "bigqueryDataset"
        )
        assert target.startswith(f"projects/{PROJECT}/datasets/{DATASET}/"), target
        assert res.get("modelDescription"), (
            f"resource {res['displayLabel']} needs a modelDescription"
        )


def test_every_finance_view_is_defined_in_the_repository(
    compiled: tuple[str, dict],
) -> None:
    _, body = compiled
    defined = set()
    for p in VIEWS_DIR.glob("*.sql"):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"CREATE\s+OR\s+REPLACE\s+VIEW\s+`[^`]*?\.(\w+)`", text, flags=re.I)
        if m:
            defined.add(m.group(1))

    for name in _resource_table_names(body):
        if name.startswith("v_"):
            assert name in defined, (
                f"{name} is a persona resource but has no deployment/data/views/*.sql"
            )


def test_skills_are_well_formed(compiled: tuple[str, dict]) -> None:
    _, body = compiled
    skills = body["skills"]
    assert len(skills) >= 3
    for skill in skills:
        assert skill["content"].startswith("---"), (
            f"{skill['skillId']}: SKILL.md needs YAML frontmatter"
        )
        assert len(skill["description"]) >= 20, (
            f"{skill['skillId']}: description is the agent search index"
        )
        for ref in skill.get("references", []):
            assert ref["referenceId"] in skill["content"]


def test_spec_rejects_bad_bigquery_resource_names(tmp_path: Path) -> None:
    bad = {
        "personaId": "default",
        "location": "global",
        "displayName": "Test Bad Spec",
        "resources": [
            {
                "displayLabel": "bad_table",
                "bigqueryResource": {"bigqueryTable": "invalid.format.table"},
            }
        ],
        "skills": [],
    }
    path = tmp_path / "default.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(sync.SpecError):
        sync.compile_persona(path, PROJECT, "global")


def test_compiled_persona_is_well_under_the_api_size_limit(
    compiled: tuple[str, dict],
) -> None:
    _, body = compiled
    payload_bytes = len(json.dumps(body).encode("utf-8"))
    assert payload_bytes < sync.MAX_PERSONA_BYTES // 10
