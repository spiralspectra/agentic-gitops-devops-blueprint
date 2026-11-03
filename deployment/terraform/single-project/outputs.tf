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

output "campaign_bucket_name" {
  description = "Campaign store bucket name for marketing studio assets."
  value       = google_storage_bucket.campaigns.name
}

output "campaign_index_table" {
  description = "BigQuery external table indexing filed campaigns."
  value       = "${var.project_id}.${google_bigquery_dataset.marketing_studio.dataset_id}.${google_bigquery_table.campaigns_index.table_id}"
}

output "user_entitlements_table" {
  description = "BigQuery table containing 4-tier RLS entitlements."
  value       = "${var.project_id}.${google_bigquery_dataset.lakehouse_sharing.dataset_id}.${google_bigquery_table.user_entitlements.table_id}"
}

output "a2ui_iframe_url" {
  description = "Public URL of the A2UI iframe frontend behind load balancer."
  value       = "https://${var.a2ui_iframe_domain}"
}

output "a2ui_iframe_lb_ip" {
  description = "Global IPv4 address of the A2UI load balancer."
  value       = google_compute_global_address.a2ui_iframe.address
}

output "a2ui_iframe_auth_mode" {
  description = "Authentication mode for A2UI frontend (iap or edge)."
  value       = var.a2ui_iframe_auth_mode
}

output "a2ui_iframe_service_name" {
  description = "Cloud Run service name for A2UI iframe frontend."
  value       = google_cloud_run_v2_service.a2ui_iframe.name
}

output "a2ui_iframe_image_repository" {
  description = "Artifact Registry Docker repository for A2UI frontend images."
  value       = local.a2ui_iframe_image_repository
}

output "dataplex_context_set_entry_group" {
  description = "Knowledge Catalog Context Set EntryGroup resource ID."
  value       = google_dataplex_entry_group.enterprise_context_set.entry_group_id
}

output "dataplex_ontology_contract_aspect_type" {
  description = "Knowledge Catalog Ontology Contract AspectType ID."
  value       = google_dataplex_aspect_type.ontology_contract.aspect_type_id
}

output "dataplex_governance_rls_aspect_type" {
  description = "Knowledge Catalog Governance RLS AspectType ID."
  value       = google_dataplex_aspect_type.governance_rls.aspect_type_id
}

output "dataplex_glossary_id" {
  description = "Knowledge Catalog Business Glossary ID."
  value       = google_dataplex_glossary.enterprise_glossary.glossary_id
}
