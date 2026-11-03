#!/usr/bin/env python3
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

"""Compile and synchronize the Google Managed AnalystAgentPersona.

Synchronizes the declarative persona specification, model instructions,
and Bring-Your-Own-Skills (BYOS) with the agenticapplications.googleapis.com API.

Sources of truth:
  finance-agent/personas/<id>.json                  persona spec
  finance-agent/personas/<id>.model_description.md  global system instructions
  finance-agent/skills/<skill_id>/SKILL.md          skill content with YAML frontmatter
  finance-agent/skills/<skill_id>/references/*.md   lazily-loaded skill references
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PERSONAS_DIR = HERE / "personas"
SKILLS_DIR = HERE / "skills"

DEFAULT_LOCATION = "global"
API_BASE = "https://agenticapplications.googleapis.com/v1"

SKILL_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
REFERENCE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
MAX_PERSONA_BYTES = 10 * 1024 * 1024  # 10 MB payload limit
ALLOWED_ROLES_PREFIX = "ANALYST_ROLE_"

MANAGED_FIELDS = (
    "displayName",
    "displayDescription",
    "modelDescription",
    "role",
    "resources",
    "skills",
    "webSearchConfig",
    "artifactsConfig",
    "mathRenderingMode",
)


class SpecError(ValueError):
    """Raised when the declarative spec is invalid."""


def load_skill(skill_id: str) -> dict[str, Any]:
    """Read skills/<skill_id>/SKILL.md (+ references/*.md) into an AnalystSkill dict."""
    if not SKILL_ID_RE.match(skill_id):
        raise SpecError(f"skill id {skill_id!r} must match {SKILL_ID_RE.pattern}")
    skill_dir = SKILLS_DIR / skill_id
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SpecError(f"missing {skill_md}")
    content = skill_md.read_text(encoding="utf-8")
    description = _frontmatter_description(content) or skill_id.replace("-", " ").replace("_", " ")

    references: list[dict[str, str]] = []
    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for ref_path in sorted(refs_dir.glob("*.md")):
            ref_id = ref_path.name
            if not REFERENCE_ID_RE.match(ref_id):
                raise SpecError(f"reference id {ref_id!r} must match {REFERENCE_ID_RE.pattern}")
            ref_content = ref_path.read_text(encoding="utf-8")
            if not ref_content.strip():
                raise SpecError(f"empty reference {ref_path}")
            # Ensure SKILL.md indexes the reference
            if f"`{ref_id}`" not in content and ref_id not in content:
                raise SpecError(f"{skill_md} does not index reference {ref_id!r}")
            references.append({"referenceId": ref_id, "content": ref_content})

    skill: dict[str, Any] = {
        "skillId": skill_id,
        "description": description,
        "content": content,
    }
    if references:
        skill["references"] = references
    return skill


def _frontmatter_description(content: str) -> str | None:
    """Return the description value from leading YAML frontmatter, if present."""
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end < 0:
        return None
    block = content[3:end]
    m = re.search(r"^description:\s*(.+?)\s*$", block, flags=re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def compile_persona(
    spec_path: Path,
    project: str,
    location: str,
    dataset: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Compile a persona spec file into (persona_id, AnalystAgentPersona body)."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    persona_id = spec["personaId"]
    if not SKILL_ID_RE.match(persona_id):
        raise SpecError(f"personaId {persona_id!r} is not a valid resource id")
    if spec.get("location", location) != location:
        raise SpecError(
            f"spec location {spec.get('location')!r} != requested location {location!r}"
        )

    model_description = spec.get("modelDescription", "")
    if spec.get("modelDescriptionFile"):
        model_description = (
            (spec_path.parent / spec["modelDescriptionFile"]).read_text(encoding="utf-8").strip()
        )

    role = spec.get("role", "ANALYST_ROLE_CORPORATE_FINANCE_ANALYST")
    if not role.startswith(ALLOWED_ROLES_PREFIX):
        raise SpecError(f"role {role!r} must be an ANALYST_ROLE_* enum value")

    raw_resources = spec.get("resources", [])
    resolved_resources = []
    target_dataset = (
        dataset
        or os.getenv("BQ_DATASET_ID")
        or os.getenv("BQ_DATASET")
        or os.getenv("APP_BQ_DATASET")
        or "enterprise_lakehouse"
    )
    for res in raw_resources:
        res_copy = json.loads(json.dumps(res))
        if "bigqueryResource" in res_copy:
            bq = res_copy["bigqueryResource"]
            for key in ("bigqueryTable", "bigqueryDataset"):
                if key in bq and isinstance(bq[key], str):
                    val = bq[key]
                    if project and project != "your-gcp-project-id":
                        val = val.replace("your-gcp-project-id", project)
                    if target_dataset != "enterprise_lakehouse":
                        val = val.replace("enterprise_lakehouse", target_dataset)
                    bq[key] = val
        resolved_resources.append(res_copy)

    body: dict[str, Any] = {
        "name": f"projects/{project}/locations/{location}/analystAgentPersonas/{persona_id}",
        "displayName": spec["displayName"],
        "displayDescription": spec.get("displayDescription", ""),
        "modelDescription": model_description,
        "role": role,
        "resources": _validate_resources(resolved_resources),
        "skills": [load_skill(s) for s in spec.get("skills", [])],
    }
    for optional in ("webSearchConfig", "artifactsConfig", "mathRenderingMode"):
        if optional in spec:
            body[optional] = spec[optional]

    seen: set[str] = set()
    for skill in body["skills"]:
        if skill["skillId"] in seen:
            raise SpecError(f"duplicate skill id {skill['skillId']!r}")
        seen.add(skill["skillId"])

    size = len(json.dumps(body).encode("utf-8"))
    if size > MAX_PERSONA_BYTES:
        raise SpecError(f"compiled persona is {size} bytes (> {MAX_PERSONA_BYTES})")
    return persona_id, body


def _validate_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels: set[str] = set()
    for res in resources:
        label = res.get("displayLabel")
        if not label:
            raise SpecError(f"resource without displayLabel: {res}")
        if label in labels:
            raise SpecError(f"duplicate resource displayLabel {label!r}")
        labels.add(label)
        kinds = [
            k
            for k in (
                "bigqueryResource",
                "googleCloudStorageResource",
                "rawFileResource",
            )
            if k in res
        ]
        if len(kinds) != 1:
            raise SpecError(f"resource {label!r} must have exactly one resource type, got {kinds}")
        if "bigqueryResource" in res:
            bq = res["bigqueryResource"]
            table, dataset = bq.get("bigqueryTable"), bq.get("bigqueryDataset")
            if bool(table) == bool(dataset):
                raise SpecError(
                    f"resource {label!r}: set exactly one of bigqueryTable / bigqueryDataset"
                )
            pattern = (
                r"^projects/[^/]+/datasets/[^/]+/tables/[^/]+$"
                if table
                else r"^projects/[^/]+/datasets/[^/]+$"
            )
            if not re.match(pattern, table or dataset):
                raise SpecError(
                    f"resource {label!r}: bad BigQuery resource name {table or dataset!r}"
                )
            if dataset and bq.get("columnDescriptions"):
                raise SpecError(
                    f"resource {label!r}: columnDescriptions is only supported with bigqueryTable"
                )
    return resources


def _session():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


def resolve_project_number(project: str) -> str:
    """Return the numeric project number; resource names require it."""
    if project.isdigit():
        return project
    session = _session()
    r = session.get(
        f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}", timeout=60
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"could not resolve the project number of {project!r} ({r.status_code}): {r.text[:300]}"
        )
    return str(r.json()["projectNumber"])


def _wait_lro(session, op_name: str, project: str, timeout_s: int = 600) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    headers = {"x-goog-user-project": project}
    while time.time() < deadline:
        r = session.get(f"{API_BASE}/{op_name}", headers=headers, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"LRO poll failed ({r.status_code}): {r.text[:500]}")
        data = r.json()
        if data.get("done"):
            if "error" in data:
                raise RuntimeError(f"LRO error: {json.dumps(data['error'])[:800]}")
            return data.get("response", {})
        time.sleep(3)
    raise TimeoutError(f"timed out waiting for {op_name}")


def upsert_persona(
    body: dict[str, Any],
    persona_id: str,
    project: str,
    project_number: str,
    location: str,
) -> dict[str, Any]:
    """Create persona if missing, otherwise PATCH managed fields."""
    session = _session()
    headers = {"Content-Type": "application/json", "x-goog-user-project": project}
    collection = f"{API_BASE}/projects/{project_number}/locations/{location}/analystAgentPersonas"
    name_url = f"{collection}/{persona_id}"

    current = session.get(name_url, headers=headers, timeout=60)
    if current.status_code == 404:
        print(f"Persona {persona_id!r} not found: creating.")
        r = session.post(
            f"{collection}?analystAgentPersonaId={persona_id}",
            headers=headers,
            data=json.dumps(body),
            timeout=120,
        )
    elif current.status_code == 200:
        print(f"Persona {persona_id!r} exists: updating managed fields.")
        r = session.patch(
            f"{name_url}?updateMask={','.join(MANAGED_FIELDS)}",
            headers=headers,
            data=json.dumps(body),
            timeout=120,
        )
    else:
        raise RuntimeError(f"GET {name_url} failed ({current.status_code}): {current.text[:800]}")

    if r.status_code >= 300:
        raise RuntimeError(f"API call failed ({r.status_code}): {r.text[:1500]}")
    op = r.json()
    if op.get("name", "").find("/operations/") >= 0 and not op.get("done"):
        print(f"Waiting for LRO {op['name']} ...")
        return _wait_lro(session, op["name"], project)
    return op.get("response", op)


def fetch_persona(
    persona_id: str, project: str, project_number: str, location: str
) -> dict[str, Any]:
    session = _session()
    r = session.get(
        f"{API_BASE}/projects/{project_number}/locations/{location}/analystAgentPersonas/{persona_id}",
        headers={"x-goog-user-project": project},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"GET failed ({r.status_code}): {r.text[:800]}")
    return r.json()


def _summary(body: dict[str, Any]) -> str:
    lines = [
        f"name:        {body['name']}",
        f"displayName: {body['displayName']}",
        f"role:        {body['role']}",
        f"resources:   {len(body['resources'])}",
    ]
    for res in body["resources"]:
        bq = res.get("bigqueryResource", {})
        target = bq.get("bigqueryTable") or bq.get("bigqueryDataset") or "(non-BigQuery)"
        lines.append(f"  - {res['displayLabel']}: {target}")
    lines.append(f"skills:      {len(body['skills'])}")
    for skill in body["skills"]:
        lines.append(
            f"  - {skill['skillId']}: {len(skill['content'])} chars, {len(skill.get('references', []))} references"
        )
    lines.append(
        f"size:        {len(json.dumps(body).encode('utf-8')):,} bytes (limit {MAX_PERSONA_BYTES:,})"
    )
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--persona",
        "--data-analytics-agent-id",
        dest="persona",
        default="default",
        help="persona id (spec file personas/<id>.json)",
    )
    p.add_argument(
        "--project",
        "--project-id",
        dest="project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id"),
        help="project id (quota project)",
    )
    p.add_argument(
        "--project-number",
        default=None,
        help="numeric project number used in resource name (resolved automatically if omitted)",
    )
    p.add_argument(
        "--dataset",
        default=os.getenv("BQ_DATASET_ID")
        or os.getenv("BQ_DATASET")
        or os.getenv("APP_BQ_DATASET")
        or "enterprise_lakehouse",
        help="BigQuery dataset containing the views (default: enterprise_lakehouse)",
    )
    p.add_argument("--location", default=DEFAULT_LOCATION, choices=["global", "us", "eu"])
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="compile and validate only without network calls",
    )
    p.add_argument(
        "--print-body",
        action="store_true",
        help="print compiled JSON payload to stdout",
    )
    p.add_argument("--show", action="store_true", help="print live persona and exit")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    offline = args.dry_run or args.print_body
    project_number = args.project_number or (
        args.project if offline else resolve_project_number(args.project)
    )

    if args.show:
        print(
            json.dumps(
                fetch_persona(args.persona, args.project, project_number, args.location),
                indent=2,
            )
        )
        return 0

    spec_path = PERSONAS_DIR / f"{args.persona}.json"
    try:
        persona_id, body = compile_persona(
            spec_path, project_number, args.location, dataset=args.dataset
        )
    except SpecError as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 2

    if args.print_body:
        print(json.dumps(body, indent=2))
        return 0
    print(_summary(body))
    if args.dry_run:
        print("\nDry run: specification compiled and verified. Nothing sent.")
        return 0

    result = upsert_persona(body, persona_id, args.project, project_number, args.location)
    print(f"\nDone: {result.get('name', '(completed)')} updateTime={result.get('updateTime')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
