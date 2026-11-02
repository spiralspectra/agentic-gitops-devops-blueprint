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

# ---------------------------------------------------------------------------
# Dedicated Service Account for the Agent Runtime
# ---------------------------------------------------------------------------

resource "google_service_account" "agent_runtime" {
  account_id   = "${var.project_name}-sa"
  display_name = "${var.project_name} - Runtime Service Account"
  description  = "Identity assumed by the Agent Runtime execution environment."
  project      = var.project_id

  depends_on = [google_project_service.services]
}

# Runtime permissions
resource "google_project_iam_member" "agent_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_project_iam_member" "agent_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_project_iam_member" "agent_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_bigquery_dataset_iam_member" "agent_bq_telemetry" {
  dataset_id = google_bigquery_dataset.telemetry.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_storage_bucket_iam_member" "agent_storage_access" {
  bucket = google_storage_bucket.agent_artifacts.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.agent_runtime.email}"
}

# ---------------------------------------------------------------------------
# Vertex AI Reasoning Engine Resource
# ---------------------------------------------------------------------------

resource "google_vertex_ai_reasoning_engine" "app" {
  display_name = var.project_name
  region       = var.region
  project      = var.project_id

  spec {
    agent_framework = "google-adk"
    identity_type   = "AGENT_IDENTITY"

    deployment_spec {
      min_instances         = 1
      max_instances         = 5
      container_concurrency = 8

      resource_limits = {
        cpu    = "2"
        memory = "4Gi"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      spec[0].source_code_spec,
      spec[0].deployment_spec,
    ]
  }

  depends_on = [google_project_service.services]
}
