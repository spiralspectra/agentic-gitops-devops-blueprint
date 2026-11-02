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

output "project_id" {
  description = "Google Cloud project ID."
  value       = var.project_id
}

output "region" {
  description = "Deployment region."
  value       = var.region
}

output "workload_identity_provider" {
  description = "Full resource name of the Workload Identity Pool Provider for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account_email" {
  description = "Email of the read-only CI Service Account for pull request checks."
  value       = google_service_account.ci.email
}

output "deployer_service_account_email" {
  description = "Email of the Deployer Service Account for main branch release deployments."
  value       = google_service_account.deployer.email
}

output "agent_runtime_service_account_email" {
  description = "Email of the Agent Runtime Service Account."
  value       = google_service_account.agent_runtime.email
}

output "telemetry_dataset_id" {
  description = "BigQuery dataset ID for agent telemetry."
  value       = google_bigquery_dataset.telemetry.dataset_id
}

output "artifacts_bucket_name" {
  description = "Cloud Storage bucket name for agent artifacts and staging."
  value       = google_storage_bucket.agent_artifacts.name
}

output "reasoning_engine_name" {
  description = "Resource name of the Vertex AI Reasoning Engine."
  value       = google_vertex_ai_reasoning_engine.app.name
}

output "reasoning_engine_id" {
  description = "Resource ID of the Vertex AI Reasoning Engine."
  value       = google_vertex_ai_reasoning_engine.app.id
}

output "logs_bucket_name" {
  description = "Cloud Storage bucket name for telemetry logs."
  value       = google_storage_bucket.telemetry_logs.name
}

