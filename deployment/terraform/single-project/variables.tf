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

variable "project_id" {
  type        = string
  description = "Google Cloud project hosting the agent service, telemetry, and CI/CD identities."
}

variable "project_name" {
  type        = string
  description = "Base name for resource naming convention (kebab-case)."
  default     = "my-agent-service"
}

variable "region" {
  type        = string
  description = "Google Cloud region for agent runtime, BigQuery datasets, and Cloud Storage."
  default     = "us-central1"
}

variable "repository_owner" {
  type        = string
  description = "GitHub repository owner (user or organization)."
}

variable "repository_name" {
  type        = string
  description = "GitHub repository name."
}

variable "tf_state_bucket" {
  type        = string
  description = "GCS bucket storing Terraform remote state (created by bootstrap.sh)."
}

variable "adopt_existing_resources" {
  type        = bool
  description = "Whether to adopt brownfield resources via declarative import blocks."
  default     = false
}

variable "reasoning_engine_id" {
  type        = string
  description = "Pre-existing Vertex AI Reasoning Engine numeric ID when adopting existing runtime."
  default     = ""
}

variable "alert_notification_email" {
  type        = string
  description = "Primary email address for SRE alert policy notifications."
  default     = "sre-alerts@example.com"
}

variable "billing_account_id" {
  type        = string
  description = "Optional Google Cloud Billing Account ID for budget alerts."
  default     = ""
}

variable "monthly_budget_amount" {
  type        = number
  description = "Monthly budget threshold in USD for billing alerts."
  default     = 500
}

variable "ci_project_roles" {
  type        = list(string)
  description = "IAM roles granted to the read-only CI service account used during pull request validation."
  default = [
    "roles/viewer",
    "roles/iam.securityReviewer",
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer",
    "roles/storage.objectViewer",
  ]
}

variable "deployer_project_roles" {
  type        = list(string)
  description = "IAM roles granted to the deployer service account restricted to refs/heads/main."
  default = [
    "roles/aiplatform.admin",
    "roles/run.admin",
    "roles/bigquery.admin",
    "roles/storage.admin",
    "roles/secretmanager.admin",
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountUser",
    "roles/monitoring.metricWriter",
    "roles/monitoring.admin",
    "roles/logging.logWriter",
    "roles/logging.admin",
  ]
}
