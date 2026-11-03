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

# Declarative brownfield resource adoption (Terraform >= 1.7)
# When adopt_existing_resources = true, Terraform plans adopt pre-existing
# resources without destructive teardowns or imperative CLI import scripts.

locals {
  adopt = (var.adopt_existing_resources || var.adopt_existing) && var.reasoning_engine_id != "" ? toset(["existing"]) : toset([])
}

import {
  for_each = local.adopt
  to       = google_vertex_ai_reasoning_engine.app
  id       = "projects/${var.project_id}/locations/${var.region}/reasoningEngines/${var.reasoning_engine_id}"
}

import {
  for_each = local.adopt
  to       = google_bigquery_dataset.telemetry
  id       = "projects/${var.project_id}/datasets/${replace("${var.project_name}_telemetry", "-", "_")}"
}

import {
  for_each = local.adopt
  to       = google_storage_bucket.agent_artifacts
  id       = "${var.project_id}-${var.project_name}-artifacts"
}

import {
  for_each = local.adopt
  to       = google_bigquery_dataset.lakehouse_sharing
  id       = "projects/${var.project_id}/datasets/${var.bq_dataset_id}"
}

import {
  for_each = local.adopt
  to       = google_bigquery_table.user_entitlements
  id       = "projects/${var.project_id}/datasets/${var.bq_dataset_id}/tables/${var.user_entitlements_table_id}"
}
