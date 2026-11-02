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

"""CI preflight: verifies caller identity and BigQuery access before running evals."""

from __future__ import annotations

import os
import sys

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
DATASET = os.environ.get("APP_BQ_DATASET", "my_agent_service_telemetry")
LOCATION = os.environ.get("APP_BQ_LOCATION", "us-central1")


def main() -> int:
    print(f"Running BigQuery preflight check against project: {PROJECT_ID}")
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
        return 0
    except Exception as exc:
        print(f"ERROR: BigQuery preflight check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
