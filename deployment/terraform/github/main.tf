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

data "github_repository" "repo" {
  full_name = "${var.repository_owner}/${var.repository_name}"
}

# ---------------------------------------------------------------------------
# GitHub Actions Secrets & Variables
# ---------------------------------------------------------------------------

locals {
  actions_secrets = {
    GCP_WORKLOAD_IDENTITY_PROVIDER = var.workload_identity_provider
    GCP_CI_SERVICE_ACCOUNT         = var.ci_service_account_email
    GCP_DEPLOYER_SERVICE_ACCOUNT   = var.deployer_service_account_email
  }

  actions_variables = {
    GCP_PROJECT_ID   = var.gcp_project_id
    GCP_REGION       = var.gcp_region
    TF_STATE_BUCKET  = var.tf_state_bucket
    TF_ALLOW_DESTROY = "false"
  }
}

resource "github_actions_secret" "secrets" {
  for_each = local.actions_secrets

  repository      = data.github_repository.repo.name
  secret_name     = each.key
  plaintext_value = each.value
}

resource "github_dependabot_secret" "dependabot_secrets" {
  for_each = local.actions_secrets

  repository      = data.github_repository.repo.name
  secret_name     = each.key
  plaintext_value = each.value
}

resource "github_actions_variable" "variables" {
  for_each = local.actions_variables

  repository    = data.github_repository.repo.name
  variable_name = each.key
  value         = each.value
}

# ---------------------------------------------------------------------------
# GitHub Deployment Environment
# ---------------------------------------------------------------------------

resource "github_repository_environment" "env" {
  repository  = data.github_repository.repo.name
  environment = var.environment_name

  can_admins_bypass   = true
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}

# ---------------------------------------------------------------------------
# Strict Branch Protection for main
# ---------------------------------------------------------------------------

resource "github_branch_protection" "main" {
  repository_id = data.github_repository.repo.node_id
  pattern       = "main"

  enforce_admins                  = var.enforce_admins
  allows_deletions                = false
  allows_force_pushes             = false
  require_conversation_resolution = true

  required_status_checks {
    strict   = true
    contexts = var.required_status_checks
  }

  dynamic "required_pull_request_reviews" {
    for_each = var.required_approving_review_count > 0 ? [1] : []
    content {
      required_approving_review_count = var.required_approving_review_count
      dismiss_stale_reviews           = true
    }
  }
}
