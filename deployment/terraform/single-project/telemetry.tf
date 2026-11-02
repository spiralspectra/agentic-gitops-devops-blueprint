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

# Layer 1 Observability: OpenTelemetry & GenAI completion logs
# Cloud Logging sink exports GenAI inference logs to BigQuery telemetry dataset.
# An authorized completions_view extracts trace_id, prompt_tokens, latency, and status.

locals {
  telemetry_dataset_id = replace("${var.project_name}_telemetry", "-", "_")
}

resource "google_storage_bucket" "telemetry_logs" {
  name                        = "${var.project_id}-${var.project_name}-logs"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}

resource "google_logging_project_sink" "genai_inference_sink" {
  name                   = "${var.project_name}-genai-sink"
  project                = var.project_id
  destination            = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.telemetry.dataset_id}"
  filter                 = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" OR labels.\"event.name\"=\"gen_ai.client.inference.operation.details\""
  unique_writer_identity = true

  depends_on = [google_bigquery_dataset.telemetry]
}

resource "google_bigquery_dataset_iam_member" "sink_bq_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.telemetry.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.genai_inference_sink.writer_identity
}

# Backing seed table for standardized operational telemetry events
resource "google_bigquery_table" "genai_telemetry_events" {
  dataset_id          = google_bigquery_dataset.telemetry.dataset_id
  table_id            = "genai_telemetry_events"
  project             = var.project_id
  description         = "Backing seed table for standardized GenAI operational telemetry events."
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  schema = jsonencode([
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "log_name"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "trace_id"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "span_id"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "model"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "prompt_tokens"
      type = "INT64"
      mode = "NULLABLE"
    },
    {
      name = "completion_tokens"
      type = "INT64"
      mode = "NULLABLE"
    },
    {
      name = "latency_ms"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "status"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "error_message"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])

  depends_on = [google_bigquery_dataset.telemetry]
}

# BigQuery view extracting standardized operational telemetry from inference logs
resource "google_bigquery_table" "completions_view" {
  dataset_id          = google_bigquery_dataset.telemetry.dataset_id
  table_id            = "completions_view"
  project             = var.project_id
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT
        timestamp,
        log_name AS logName,
        trace_id,
        span_id,
        model,
        prompt_tokens,
        completion_tokens,
        latency_ms,
        status,
        error_message
      FROM
        `${var.project_id}.${google_bigquery_dataset.telemetry.dataset_id}.genai_telemetry_events`
      WHERE
        trace_id IS NOT NULL
    SQL
  }

  depends_on = [google_bigquery_table.genai_telemetry_events]
}
