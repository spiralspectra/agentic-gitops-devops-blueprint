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

# Gemini for Financial Services - "Financial Research agent" (Agentis Finance
# / FP&A agent).
#
# Terraform manages the project-side enablement: APIs, IAM roles allowing users
# to chat with the agent and query BigQuery under their own identity, and the
# admin role for the release pipeline.
#
# Access model (least-privilege 4-tier RLS + PII isolation):
#   - roles/agenticapplications.user: chat with the agent (GE / A2A)
#   - roles/bigquery.jobUser: run BigQuery jobs as the user
#   - roles/serviceusage.serviceUsageConsumer: quota project for BigQuery MCP tools
#   - roles/mcp.toolUser: call BigQuery MCP tools
#   - retail pilot users get the same roles minus roles/agenticapplications.user
#   - table/view-level roles/bigquery.dataViewer ONLY on approved Authorized Views
#     and non-PII reference tables — NEVER dataset-wide on lakehouse_sharing.

locals {
  finance_agent_user_project_roles = [
    "roles/agenticapplications.user",
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
    "roles/dataplex.catalogViewer",
    "roles/dataplex.contentUser",
    "roles/dataplex.viewer",
    "roles/discoveryengine.agentUser",
    "roles/discoveryengine.user",
    "roles/discoveryengine.viewer",
    "roles/mcp.toolUser",
    "roles/serviceusage.serviceUsageConsumer",
  ]

  finance_agent_user_bindings = {
    for pair in setproduct(var.finance_agent_user_members, local.finance_agent_user_project_roles) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], role = pair[1] }
  }

  # Approved views and non-PII reference tables queryable by end users
  lakehouse_user_readable_objects = var.lakehouse_hydrated ? [
    "v_operations",
    "v_catalog_enriched",
    "v_finance_transactions",
    "v_finance_receipts",
    "v_finance_customer_bridge",
    "branch",
    "supplier",
    "customermosaicdemographics",
  ] : []

  finance_agent_table_bindings = {
    for pair in setproduct(var.finance_agent_user_members, local.lakehouse_user_readable_objects) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], table_id = pair[1] }
  }

  # Retail pilot users: same as finance minus roles/agenticapplications.user
  pilot_retail_user_project_roles = [
    for role in local.finance_agent_user_project_roles : role
    if role != "roles/agenticapplications.user"
  ]

  pilot_retail_user_bindings = {
    for pair in setproduct(var.pilot_retail_user_members, local.pilot_retail_user_project_roles) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], role = pair[1] }
  }

  lakehouse_retail_readable_objects = var.lakehouse_hydrated ? [
    "v_operations",
    "v_catalog_enriched",
    "v_finance_customer_bridge",
    "branch",
    "supplier",
    "customermosaicdemographics",
  ] : []

  pilot_retail_table_bindings = {
    for pair in setproduct(var.pilot_retail_user_members, local.lakehouse_retail_readable_objects) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], table_id = pair[1] }
  }
}

# Analysts and finance pilot users
resource "google_project_iam_member" "finance_agent_users" {
  for_each = local.finance_agent_user_bindings

  project = var.project_id
  role    = each.value.role
  member  = each.value.member

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table_iam_member" "finance_agent_users_allowed_objects" {
  for_each = local.finance_agent_table_bindings

  project    = var.project_id
  dataset_id = google_bigquery_dataset.lakehouse_sharing.dataset_id
  table_id   = each.value.table_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value.member
}

# Retail pilot users
resource "google_project_iam_member" "retail_pilot_users" {
  for_each = local.pilot_retail_user_bindings

  project = var.project_id
  role    = each.value.role
  member  = each.value.member

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table_iam_member" "retail_pilot_users_allowed_objects" {
  for_each = local.pilot_retail_table_bindings

  project    = var.project_id
  dataset_id = google_bigquery_dataset.lakehouse_sharing.dataset_id
  table_id   = each.value.table_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value.member
}

# Optional Spark demo dataset access
resource "google_bigquery_dataset_iam_member" "deployer_spark_demo_owner" {
  count = var.spark_demo_dataset_id != "" ? 1 : 0

  project    = var.project_id
  dataset_id = var.spark_demo_dataset_id
  role       = "roles/bigquery.dataOwner"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_bigquery_dataset_iam_member" "users_spark_demo_viewer" {
  for_each = var.spark_demo_dataset_id != "" ? toset(concat(var.finance_agent_user_members, var.pilot_retail_user_members)) : toset([])

  project    = var.project_id
  dataset_id = var.spark_demo_dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value

  depends_on = [google_bigquery_dataset_iam_member.deployer_spark_demo_owner]
}

# Persona administrators
resource "google_project_iam_member" "finance_agent_admins" {
  for_each = toset(var.finance_agent_admin_members)

  project = var.project_id
  role    = "roles/agenticapplications.admin"
  member  = each.value

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "finance_agent_deployer_admin" {
  project = var.project_id
  role    = "roles/agenticapplications.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"

  depends_on = [google_project_service.services]
}

# State migration example demonstrating zero-downtime transition of roles
moved {
  from = google_project_iam_member.finance_agent_users["user:pilot-user@example.com|roles/aiplatform.user"]
  to   = google_project_iam_member.retail_pilot_users["user:pilot-user@example.com|roles/aiplatform.user"]
}
