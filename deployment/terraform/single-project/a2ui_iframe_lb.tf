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

# Front door of the a2ui-iframe Cloud Run service:
#
#   browser (Gemini Enterprise iframe)
#     └─► https://<a2ui_iframe_domain>          global external HTTPS LB (EXTERNAL_MANAGED)
#           ├─ Certificate Manager cert          DNS-authorised, auto-renewed
#           ├─ Cloud Armor                       allowlist of egress CIDRs (empty = allow all)
#           ├─ IAP (auth mode "iap")             Google sign-in, authorised by a2ui_iframe_iap_members
#           └─► serverless NEG ─► Cloud Run a2ui-iframe (ingress: load balancer only)
#
# Two auth modes (var.a2ui_iframe_auth_mode):
#   iap  - IAP on the backend service; Cloud Run keeps its invoker IAM check
#          with IAP's service agent as the only invoker.
#   edge - no sign-in; Cloud Armor is the only gate and Cloud Run disables its
#          invoker check.

locals {
  a2ui_iap          = var.a2ui_iframe_auth_mode == "iap"
  iap_service_agent = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
  a2ui_dns_enabled  = var.a2ui_iframe_dns != null
}

# ---------------------------------------------------------------------------
# Address, NEG, Cloud Armor, backend
# ---------------------------------------------------------------------------

resource "google_compute_global_address" "a2ui_iframe" {
  name         = "a2ui-iframe-ip"
  project      = var.project_id
  ip_version   = "IPV4"
  address_type = "EXTERNAL"

  depends_on = [google_project_service.services]
}

resource "google_compute_region_network_endpoint_group" "a2ui_iframe" {
  name                  = "a2ui-iframe-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.a2ui_iframe.name
  }
}

# Allowlist by source CIDR. With an empty list the policy allows everything
# (IAP / application are the primary gates); when allowed CIDRs are specified,
# the default rule flips to deny(403).
resource "google_compute_security_policy" "a2ui_iframe" {
  name        = "a2ui-iframe-armor"
  project     = var.project_id
  type        = "CLOUD_ARMOR"
  description = "Edge allowlist for the A2UI iframe frontend."

  dynamic "rule" {
    for_each = chunklist(var.a2ui_iframe_allowed_cidrs, 10)
    content {
      action      = "allow"
      priority    = 1000 + rule.key
      description = "Allowlisted egress ranges (${rule.key + 1})"
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = rule.value
        }
      }
    }
  }

  rule {
    action      = length(var.a2ui_iframe_allowed_cidrs) > 0 ? "deny(403)" : "allow"
    priority    = 2147483647
    description = "Default rule"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_compute_backend_service" "a2ui_iframe" {
  name                  = "a2ui-iframe-backend"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  security_policy       = google_compute_security_policy.a2ui_iframe.id

  backend {
    group = google_compute_region_network_endpoint_group.a2ui_iframe.id
  }

  dynamic "iap" {
    for_each = local.a2ui_iap ? [1] : []
    content {
      enabled = true
    }
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Who may pass IAP (auth mode "iap")
resource "google_iap_web_backend_service_iam_member" "a2ui_iframe" {
  for_each = local.a2ui_iap ? toset(var.a2ui_iframe_iap_members) : toset([])

  project             = var.project_id
  web_backend_service = google_compute_backend_service.a2ui_iframe.name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

# ---------------------------------------------------------------------------
# Certificate Manager & HTTPS Front Door
# ---------------------------------------------------------------------------

resource "google_certificate_manager_dns_authorization" "a2ui_iframe" {
  name     = "a2ui-iframe-dns-auth"
  project  = var.project_id
  location = "global"
  domain   = var.a2ui_iframe_domain

  depends_on = [google_project_service.services]
}

resource "google_certificate_manager_certificate" "a2ui_iframe" {
  name     = "a2ui-iframe-cert"
  project  = var.project_id
  location = "global"

  managed {
    domains            = [var.a2ui_iframe_domain]
    dns_authorizations = [google_certificate_manager_dns_authorization.a2ui_iframe.id]
  }
}

resource "google_certificate_manager_certificate_map" "a2ui_iframe" {
  name    = "a2ui-iframe-cert-map"
  project = var.project_id
}

resource "google_certificate_manager_certificate_map_entry" "a2ui_iframe" {
  name         = "a2ui-iframe-cert-map-entry"
  project      = var.project_id
  map          = google_certificate_manager_certificate_map.a2ui_iframe.name
  certificates = [google_certificate_manager_certificate.a2ui_iframe.id]
  hostname     = var.a2ui_iframe_domain
}

resource "google_compute_url_map" "a2ui_iframe" {
  name            = "a2ui-iframe-lb"
  project         = var.project_id
  default_service = google_compute_backend_service.a2ui_iframe.id
}

resource "google_compute_target_https_proxy" "a2ui_iframe" {
  name            = "a2ui-iframe-https-proxy"
  project         = var.project_id
  url_map         = google_compute_url_map.a2ui_iframe.id
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.a2ui_iframe.id}"
}

resource "google_compute_global_forwarding_rule" "a2ui_iframe_https" {
  name                  = "a2ui-iframe-https"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "443"
  target                = google_compute_target_https_proxy.a2ui_iframe.id
  ip_address            = google_compute_global_address.a2ui_iframe.id
}

# HTTP -> HTTPS redirect
resource "google_compute_url_map" "a2ui_iframe_redirect" {
  name    = "a2ui-iframe-https-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "a2ui_iframe_redirect" {
  name    = "a2ui-iframe-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.a2ui_iframe_redirect.id
}

resource "google_compute_global_forwarding_rule" "a2ui_iframe_http" {
  name                  = "a2ui-iframe-http"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "80"
  target                = google_compute_target_http_proxy.a2ui_iframe_redirect.id
  ip_address            = google_compute_global_address.a2ui_iframe.id
}

# ---------------------------------------------------------------------------
# Cloud DNS Record Sets (when var.a2ui_iframe_dns is supplied)
# ---------------------------------------------------------------------------

resource "google_dns_record_set" "a2ui_iframe_a" {
  count = local.a2ui_dns_enabled ? 1 : 0

  project      = var.a2ui_iframe_dns.project
  managed_zone = var.a2ui_iframe_dns.zone
  name         = "${var.a2ui_iframe_domain}."
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.a2ui_iframe.address]
}

resource "google_dns_record_set" "a2ui_iframe_cert_auth" {
  count = local.a2ui_dns_enabled ? 1 : 0

  project      = var.a2ui_iframe_dns.project
  managed_zone = var.a2ui_iframe_dns.zone
  name         = google_certificate_manager_dns_authorization.a2ui_iframe.dns_resource_record[0].name
  type         = google_certificate_manager_dns_authorization.a2ui_iframe.dns_resource_record[0].type
  ttl          = 300
  rrdatas      = [google_certificate_manager_dns_authorization.a2ui_iframe.dns_resource_record[0].data]
}
