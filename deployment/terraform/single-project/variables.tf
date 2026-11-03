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
  default     = "europe-west2"
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

variable "adopt_existing" {
  type        = bool
  description = "Alias for adopt_existing_resources."
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

# ---------------------------------------------------------------------------
# BigQuery & Lakehouse Governance Variables
# ---------------------------------------------------------------------------

variable "bq_dataset_id" {
  type        = string
  description = "BigQuery dataset holding hydrated tables and views."
  default     = "lakehouse_sharing"
}

variable "lakehouse_hydrated" {
  type        = bool
  description = "true once lakehouse sync script has populated views and tables, enabling table-level IAM."
  default     = false
}

variable "user_entitlements_table_id" {
  type        = string
  description = "Table mapping SESSION_USER() to 4-tier RLS roles."
  default     = "user_entitlements"
}

variable "marketing_dataset_id" {
  type        = string
  description = "BigQuery dataset for marketing studio index."
  default     = "enterprise_marketing_studio"
}

variable "campaign_index_table_id" {
  type        = string
  description = "External table in marketing_dataset_id over campaign files."
  default     = "campaigns_index"
}

variable "spark_demo_dataset_id" {
  type        = string
  description = "Optional dataset ID for desktop Gemini Enterprise demo views."
  default     = ""
}

# ---------------------------------------------------------------------------
# A2UI iframe frontend variables
# ---------------------------------------------------------------------------

variable "a2ui_iframe_domain" {
  type        = string
  description = "Hostname served by a2ui-iframe load balancer, allowlisted for WebFrameUrl."
  default     = "a2ui.example.com"
}

variable "a2ui_iframe_dns" {
  type = object({
    project = string
    zone    = string
  })
  description = "Cloud DNS managed zone hosting a2ui_iframe_domain; null = managed externally."
  default     = null
}

variable "a2ui_iframe_auth_mode" {
  type        = string
  description = "Auth mode: iap (IAP sign-in) or edge (Cloud Armor allowlist only)."
  default     = "iap"

  validation {
    condition     = contains(["iap", "edge"], var.a2ui_iframe_auth_mode)
    error_message = "a2ui_iframe_auth_mode must be 'iap' or 'edge'."
  }
}

variable "a2ui_iframe_iap_members" {
  type        = list(string)
  description = "IAM members granted roles/iap.httpsResourceAccessor in iap auth mode."
  default     = []
}

variable "a2ui_iframe_allowed_cidrs" {
  type        = list(string)
  description = "Cloud Armor source CIDRs allowlist. Empty = allow all."
  default     = []
}

variable "gemini_enterprise_app_id" {
  type        = string
  description = "Gemini Enterprise application full resource name."
  default     = ""
}

# ---------------------------------------------------------------------------
# Agentic Applications & Finance Agent variables
# ---------------------------------------------------------------------------

variable "finance_agent_user_members" {
  type        = list(string)
  description = "IAM members who may use Financial Research agent and full finance views."
  default     = []
}

variable "pilot_retail_user_members" {
  type        = list(string)
  description = "IAM members who use retail agent without finance views."
  default     = []
}

variable "finance_agent_admin_members" {
  type        = list(string)
  description = "IAM members who manage agent personas in Admin UI."
  default     = []
}
