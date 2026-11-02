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

locals {
  repository_full_name = "${var.repository_owner}/${var.repository_name}"
  ci_sa_id             = "${var.project_name}-ci"
  deployer_sa_id       = "${var.project_name}-deployer"
  wif_pool_id          = "github-actions-pool"
  wif_provider_id      = "github-actions-provider"
}

# ---------------------------------------------------------------------------
# Workload Identity Federation: Keyless GitHub Actions Authentication
# ---------------------------------------------------------------------------

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = local.wif_pool_id
  project                   = var.project_id
  display_name              = "GitHub Actions WIF Pool"
  description               = "Federates GitHub Actions OIDC tokens for ${local.repository_full_name}."

  depends_on = [google_project_service.services]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_provider_id = local.wif_provider_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  project                            = var.project_id
  display_name                       = "GitHub OIDC Provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
    "attribute.event_name"       = "assertion.event_name"
  }

  attribute_condition = "assertion.repository == '${local.repository_full_name}'"
}

locals {
  wif_pool_name            = google_iam_workload_identity_pool.github.name
  principal_set_repository = "principalSet://iam.googleapis.com/${local.wif_pool_name}/attribute.repository/${local.repository_full_name}"
  principal_set_main       = "principalSet://iam.googleapis.com/${local.wif_pool_name}/attribute.ref/refs/heads/main"
}

# ---------------------------------------------------------------------------
# Dual Service Account Model
# ---------------------------------------------------------------------------

# CI Service Account: Read-only on infrastructure, used for pull requests
resource "google_service_account" "ci" {
  account_id   = local.ci_sa_id
  display_name = "${var.project_name} - GitHub Actions CI (PR validation)"
  description  = "Impersonated by any workflow run from ${local.repository_full_name}. Read-only on infrastructure."
  project      = var.project_id

  depends_on = [google_project_service.services]
}

# Deployer Service Account: Full deploy permissions, strictly locked to refs/heads/main
resource "google_service_account" "deployer" {
  account_id   = local.deployer_sa_id
  display_name = "${var.project_name} - GitHub Actions Deployer (Main only)"
  description  = "Impersonated strictly by runs on refs/heads/main of ${local.repository_full_name}. Applies Terraform and deploys."
  project      = var.project_id

  depends_on = [google_project_service.services]
}

# Workload Identity user bindings
resource "google_service_account_iam_member" "ci_wif_user" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.principal_set_repository
}

resource "google_service_account_iam_member" "ci_token_creator" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.principal_set_repository
}

resource "google_service_account_iam_member" "deployer_wif_user" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.principal_set_main
}

resource "google_service_account_iam_member" "deployer_token_creator" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.principal_set_main
}

# Project level role grants
resource "google_project_iam_member" "ci_roles" {
  for_each = toset(var.ci_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_project_iam_member" "deployer_roles" {
  for_each = toset(var.deployer_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Terraform state bucket access (CI reads without lock; Deployer reads/writes)
resource "google_storage_bucket_iam_member" "ci_tfstate_reader" {
  bucket = var.tf_state_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_storage_bucket_iam_member" "deployer_tfstate_admin" {
  bucket = var.tf_state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.deployer.email}"
}
