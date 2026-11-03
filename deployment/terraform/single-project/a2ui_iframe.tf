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

# `a2ui-iframe` — Cloud Run service that hosts the custom A2UI frontend the
# agent renders inside Gemini Enterprise with the `WebFrameUrl` component.
#
# Gemini Enterprise renders allowlisted domains in the WebFrameUrl iframe.
# Terraform creates the service with a placeholder container so the URL is
# stable from day one; the actual frontend is deployed onto it via CI/CD.
#
# Ingress is restricted to the external HTTPS load balancer in a2ui_iframe_lb.tf.
#
# Ownership split: Terraform owns the service's existence, URL, ingress,
# identity and access; deployment workflows own the container image, env vars
# and revision settings (`lifecycle.ignore_changes`).

resource "google_service_account" "a2ui_iframe" {
  account_id   = "${var.project_name}-a2ui-iframe"
  display_name = "${var.project_name} - A2UI iframe frontend (Cloud Run)"
  description  = "Runtime identity of the a2ui-iframe Cloud Run service. No project roles: the frontend communicates with the agent through A2UI postMessage actions."
  project      = var.project_id

  depends_on = [google_project_service.services]
}

resource "google_cloud_run_v2_service" "a2ui_iframe" {
  name     = "a2ui-iframe"
  location = var.region
  project  = var.project_id

  description         = "Custom A2UI frontend rendered by Gemini Enterprise via WebFrameUrl (placeholder container until frontend deploy)."
  ingress             = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  deletion_protection = true

  # "iap" mode (default): invoker IAM check is enabled; only IAP service agent invokes.
  # "edge" mode: invoker IAM check is disabled; Cloud Armor acts as the edge gate.
  invoker_iam_disabled = !local.a2ui_iap

  template {
    service_account = google_service_account.a2ui_iframe.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      template[0].containers,
      template[0].labels,
      template[0].annotations,
      template[0].revision,
      template[0].scaling,
      labels,
      annotations,
      client,
      client_version,
      build_config,
    ]
  }

  depends_on = [google_project_service.services]
}

# IAP service agent is granted invoker role in "iap" mode
resource "google_cloud_run_v2_service_iam_member" "a2ui_iframe_iap_invoker" {
  count = local.a2ui_iap ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.a2ui_iframe.location
  name     = google_cloud_run_v2_service.a2ui_iframe.name
  role     = "roles/run.invoker"
  member   = local.iap_service_agent
}

# ---------------------------------------------------------------------------
# Artifact Registry image repository for A2UI frontend
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "a2ui_iframe" {
  repository_id = "a2ui-iframe"
  project       = var.project_id
  location      = var.region
  format        = "DOCKER"
  description   = "Docker repository for A2UI iframe frontend images."

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-recent-releases"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_artifact_registry_repository_iam_member" "a2ui_iframe_deployer_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.a2ui_iframe.location
  repository = google_artifact_registry_repository.a2ui_iframe.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

locals {
  a2ui_iframe_image_repository = "${google_artifact_registry_repository.a2ui_iframe.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.a2ui_iframe.repository_id}"
}
