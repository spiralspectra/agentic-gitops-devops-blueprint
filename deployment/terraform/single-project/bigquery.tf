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

resource "google_bigquery_dataset" "telemetry" {
  dataset_id  = replace("${var.project_name}_telemetry", "-", "_")
  project     = var.project_id
  location    = var.region
  description = "Dataset for agent evaluation metrics, execution traces, and telemetry logs."

  labels = {
    env = "production"
    app = var.project_name
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "agent_evals" {
  dataset_id          = google_bigquery_dataset.telemetry.dataset_id
  table_id            = "evaluation_metrics"
  project             = var.project_id
  description         = "Audit and regression evaluation results recorded across CI and release workflows."
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  schema = jsonencode([
    {
      name = "run_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "commit_sha"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "branch"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "score"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "passed"
      type = "BOOLEAN"
      mode = "REQUIRED"
    },
    {
      name = "details"
      type = "JSON"
      mode = "NULLABLE"
    }
  ])
}
