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

data "google_project" "project" {
  project_id = var.project_id
}

locals {
  logs_bucket_name     = "${var.project_id}-${var.project_name}-logs"
  campaign_bucket_name = "${var.project_id}-${var.project_name}-campaigns"

  # Agent Runtime's platform service agent
  agent_runtime_service_agent = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

  # Effective Agent Runtime identity
  agent_identity_member = length(try(google_vertex_ai_reasoning_engine.app.spec[0].effective_identity, "")) > 0 ? "principal://${google_vertex_ai_reasoning_engine.app.spec[0].effective_identity}" : "serviceAccount:${google_service_account.agent_runtime.email}"
}
