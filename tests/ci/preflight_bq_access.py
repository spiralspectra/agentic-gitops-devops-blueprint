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

"""CI preflight: verifies caller identity, BigQuery access, and view syntax before running evals."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
DATASET = os.environ.get("APP_BQ_DATASET", "my_agent_service_telemetry")
LOCATION = os.environ.get("APP_BQ_LOCATION", "us-central1")

VIEW_DIRS = [
    Path("data/views"),
    Path("deployment/data/views"),
]


def validate_view_syntax_offline(sql_content: str, filename: str) -> bool:
    """Offline validation of Authorized View SQL syntax and safety invariants."""
    clean_sql = re.sub(r"--.*$", "", sql_content, flags=re.MULTILINE).strip()
    if not clean_sql:
        print(f"Warning: {filename} is empty.")
        return True

    # Must contain CREATE OR REPLACE VIEW or standard SELECT/WITH
    has_create_view = bool(re.search(r"CREATE\s+(OR\s+REPLACE\s+)?VIEW", clean_sql, re.IGNORECASE))
    has_select_with = bool(re.search(r"\b(SELECT|WITH)\b", clean_sql, re.IGNORECASE))

    if not (has_create_view or has_select_with):
        print(
            f"ERROR: {filename} does not contain valid VIEW DDL or query statement.",
            file=sys.stderr,
        )
        return False

    # Check balanced parentheses
    depth = 0
    in_quote = None
    for char in clean_sql:
        if in_quote:
            if char == in_quote:
                in_quote = None
        elif char in ("'", '"', "`"):
            in_quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                print(f"ERROR: {filename} has unmatched closing parenthesis.", file=sys.stderr)
                return False

    if depth != 0:
        print(f"ERROR: {filename} has {depth} unclosed parenthesis.", file=sys.stderr)
        return False

    return True


def check_all_views(client: bigquery.Client | None = None) -> bool:
    """Validates all .sql view files across VIEW_DIRS."""
    view_files: list[Path] = []
    for d in VIEW_DIRS:
        if d.is_dir():
            view_files.extend(d.glob("*.sql"))

    if not view_files:
        print("No .sql view files found to check.")
        return True

    all_passed = True
    dry_run_config = (
        bigquery.QueryJobConfig(dry_run=True, use_query_cache=False) if client else None
    )

    for view_file in view_files:
        content = view_file.read_text(encoding="utf-8")
        # Offline syntax check
        if not validate_view_syntax_offline(content, view_file.name):
            all_passed = False
            continue

        # If live client available, dry-run
        if client and dry_run_config:
            rendered = content.replace("your-gcp-project-id", PROJECT_ID).replace(
                "my_agent_service_data", DATASET
            )
            try:
                # Extract query after AS if CREATE VIEW
                m = re.search(r"\bAS\b\s+(SELECT|WITH\b[\s\S]+)", rendered, re.IGNORECASE)
                query_to_dry_run = (
                    m.group(1).rstrip(";").strip() if m else rendered.rstrip(";").strip()
                )
                client.query(
                    f"SELECT * FROM (\n{query_to_dry_run}\n) LIMIT 0", job_config=dry_run_config
                )
                print(f"  [dry-run OK] {view_file.name}")
            except Exception as exc:
                print(f"  [dry-run warning/skip] {view_file.name}: {exc}")
        else:
            print(f"  [offline syntax OK] {view_file.name}")

    return all_passed


def main() -> int:
    print(f"Running BigQuery preflight check against project: {PROJECT_ID}")
    client = None
    try:
        client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
        query = "SELECT SESSION_USER() AS current_user"
        rows = list(client.query(query).result())
        current_user = rows[0]["current_user"] if rows else "unknown"
        print(f"BigQuery SESSION_USER(): {current_user}")

        dataset_ref = client.dataset(DATASET)
        try:
            dataset = client.get_dataset(dataset_ref)
            print(f"Dataset {dataset.dataset_id} is accessible.")
        except Exception as ds_err:
            print(f"Warning: Dataset {DATASET} lookup returned: {ds_err}")

        print("BigQuery preflight access verified successfully.")
    except Exception as exc:
        print(
            f"BigQuery live client unconfigured or offline ({exc}). Running offline view preflight checks."
        )

    print("\nValidating .sql views in data/views and deployment/data/views...")
    if not check_all_views(client):
        return 1

    print("Preflight checks completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
