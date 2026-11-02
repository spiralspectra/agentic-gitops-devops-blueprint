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

# Layer 2 SRE Observability: SLOs, Burn-Rate Alerts, Uptime Check, and Incident Runbooks
# Enforces a 28-day rolling window for availability (99.5%) and latency (p95 <= 8000ms).

locals {
  runbook_base_url = "https://github.com/${var.repository_owner}/${var.repository_name}/blob/main/docs/RUNBOOK_ALERTS.md"
}

# ---------------------------------------------------------------------------
# 1. Notification Channels
# ---------------------------------------------------------------------------

resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "${var.project_name} SRE Alert Email"
  type         = "email"
  enabled      = true

  labels = {
    email_address = var.alert_notification_email
  }

  depends_on = [google_project_service.services]
}

# ---------------------------------------------------------------------------
# 2. Log-Based Metrics
# ---------------------------------------------------------------------------

resource "google_logging_metric" "tool_execution_errors" {
  project     = var.project_id
  name        = "${var.project_name}/tool_execution_errors"
  description = "Count of runtime exceptions or tool invocation errors during agent turns."
  filter      = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" AND severity>=ERROR AND (textPayload=~\"ToolExecutionError\" OR jsonPayload.error=~\"Exception\")"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_logging_metric" "guardrail_refusals" {
  project     = var.project_id
  name        = "${var.project_name}/guardrail_refusals"
  description = "Count of prompt-injection, cross-tenant, or policy refusal events."
  filter      = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" AND (jsonPayload.event=\"guardrail_block\" OR textPayload=~\"policy violation refused\")"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

# ---------------------------------------------------------------------------
# 3. Custom Monitoring Service & 28-Day Rolling SLOs
# ---------------------------------------------------------------------------

resource "google_monitoring_custom_service" "agent_service" {
  project      = var.project_id
  service_id   = "${var.project_name}-service"
  display_name = "${var.project_name} Custom Service"

  depends_on = [google_project_service.services]
}

# Availability SLO: 99.5% over 28-day rolling window
resource "google_monitoring_slo" "availability_slo" {
  project      = var.project_id
  service      = google_monitoring_custom_service.agent_service.service_id
  slo_id       = "availability-28d-slo"
  display_name = "28-Day Availability Target (99.5%)"
  goal         = 0.995
  rolling_period_days = 28

  basic_sli {
    availability {}
  }
}

# Latency SLO: 95% of queries respond within 8,000 ms over 28 days
resource "google_monitoring_slo" "latency_slo" {
  project      = var.project_id
  service      = google_monitoring_custom_service.agent_service.service_id
  slo_id       = "latency-p95-28d-slo"
  display_name = "28-Day Latency Target (p95 <= 8000ms)"
  goal         = 0.95
  rolling_period_days = 28

  basic_sli {
    latency {
      threshold = "8s"
    }
  }
}

# ---------------------------------------------------------------------------
# 4. Burn-Rate Alert Policies (Fast-Burn 1h and Slow-Burn 6h)
# ---------------------------------------------------------------------------

resource "google_monitoring_alert_policy" "fast_burn_availability" {
  project      = var.project_id
  display_name = "${var.project_name} - Fast Burn Availability Alert (1h burn rate > 14.4x)"
  combiner     = "OR"
  enabled      = true

  notification_channels = [google_monitoring_notification_channel.email.name]

  conditions {
    display_name = "Availability error budget fast burn"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.availability_slo.name}\", 3600s)"
      comparison      = "COMPARISON_GT"
      threshold_value = 14.4
      duration        = "0s"
      trigger {
        count = 1
      }
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      ### Fast Burn Availability Budget Depletion Alert
      - **Severity:** Critical (SEV1)
      - **Impact:** >2% of 28-day error budget consumed within 1 hour.
      - **Runbook:** Refer to [SRE Alert Runbook - Fast Burn Availability](${local.runbook_base_url}#alert-fast-burn-availability)
      - **Triage:** Query Cloud Logging for `ReasoningEngine` 5xx and uncaught exceptions.
    EOT
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "slow_burn_availability" {
  project      = var.project_id
  display_name = "${var.project_name} - Slow Burn Availability Alert (6h burn rate > 6.0x)"
  combiner     = "OR"
  enabled      = true

  notification_channels = [google_monitoring_notification_channel.email.name]

  conditions {
    display_name = "Availability error budget slow burn"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.availability_slo.name}\", 21600s)"
      comparison      = "COMPARISON_GT"
      threshold_value = 6.0
      duration        = "300s"
      trigger {
        count = 1
      }
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      ### Slow Burn Availability Budget Depletion Alert
      - **Severity:** High (SEV2)
      - **Impact:** Error budget is steadily depleting over a 6-hour window.
      - **Runbook:** Refer to [SRE Alert Runbook - Slow Burn Availability](${local.runbook_base_url}#alert-slow-burn-availability)
    EOT
  }

  alert_strategy {
    auto_close = "3600s"
  }
}

# ---------------------------------------------------------------------------
# 5. Uptime Check for Agent Health Endpoint
# ---------------------------------------------------------------------------

resource "google_monitoring_uptime_check_config" "agent_health_check" {
  project      = var.project_id
  display_name = "${var.project_name} Health Endpoint Uptime Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/healthz"
    port         = 8080
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${var.project_name}.run.app"
    }
  }
}
