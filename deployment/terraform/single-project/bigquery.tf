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

# ---------------------------------------------------------------------------
# Lakehouse Hydration & Governance Dataset
# ---------------------------------------------------------------------------

resource "google_bigquery_dataset" "lakehouse_sharing" {
  dataset_id                 = var.bq_dataset_id
  project                    = var.project_id
  location                   = var.region
  description                = "Lakehouse sharing and cross-cloud hydrated tables dataset"
  delete_contents_on_destroy = false

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      access,
      labels,
      friendly_name,
      description,
      max_time_travel_hours,
      default_table_expiration_ms,
      default_partition_expiration_ms,
    ]
  }

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "user_entitlements" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.lakehouse_sharing.dataset_id
  table_id            = var.user_entitlements_table_id
  description         = "Maps a BigQuery SESSION_USER() to 4-tier RLS role for data governance."
  deletion_protection = true

  schema = jsonencode([
    { name = "user_email", type = "STRING", mode = "NULLABLE", description = "Identity e-mail as returned by SESSION_USER()." },
    { name = "wif_subject", type = "STRING", mode = "NULLABLE", description = "WIF subject for federated callers." },
    { name = "role", type = "STRING", mode = "NULLABLE", description = "BRANCH_STAFF | BRANCH_MANAGER | REGIONAL_MANAGER | DIVISIONAL_HEAD." },
    { name = "branch_id", type = "STRING", mode = "NULLABLE", description = "Branch scope ('*' = any)." },
    { name = "username", type = "STRING", mode = "NULLABLE", description = "Username scope ('*' = any)." },
    { name = "region_group", type = "STRING", mode = "NULLABLE", description = "Region scope ('ALL' = any)." },
    { name = "division", type = "STRING", mode = "NULLABLE", description = "Division scope ('ALL' = every row)." },
  ])

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [schema, labels, description]
  }
}

resource "google_bigquery_table_iam_member" "ci_allowed_objects" {
  for_each = toset(local.lakehouse_user_readable_objects)

  project    = var.project_id
  dataset_id = google_bigquery_dataset.lakehouse_sharing.dataset_id
  table_id   = each.value
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_bigquery_dataset_iam_member" "deployer_data_owner" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.lakehouse_sharing.dataset_id
  role       = "roles/bigquery.dataOwner"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}
