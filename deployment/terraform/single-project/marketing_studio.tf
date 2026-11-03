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

# Pillar 3 Marketing Studio — campaign store.
#
# GCS is the system of record for every campaign filed by the studio
# (campaigns/<campaign_id>/campaign.json, index.json, assets/*). A BigQuery
# external table over the one-line index.json files makes campaigns searchable
# via SQL (search_campaigns tool) without requiring a second write path.

resource "google_storage_bucket" "campaigns" {
  name                        = local.campaign_bucket_name
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 90
      with_state                 = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.services]
}

# Agent files campaigns and assets under its own identity
resource "google_storage_bucket_iam_member" "agent_identity_campaigns_bucket" {
  bucket = google_storage_bucket.campaigns.name
  role   = "roles/storage.objectAdmin"
  member = local.agent_identity_member
}

resource "google_bigquery_dataset" "marketing_studio" {
  dataset_id                 = var.marketing_dataset_id
  project                    = var.project_id
  location                   = var.region
  description                = "Pillar 3 marketing studio: searchable index of filed campaigns (external table over campaign bucket)."
  delete_contents_on_destroy = false

  lifecycle {
    ignore_changes = [access, labels]
  }

  depends_on = [google_project_service.services]
}

# External table over gs://.../campaigns/*/index.json
resource "google_bigquery_table" "campaigns_index" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.marketing_studio.dataset_id
  table_id            = var.campaign_index_table_id
  description         = "Searchable index of Pillar 3 marketing campaigns. Source of truth: gs://${google_storage_bucket.campaigns.name}/campaigns/<campaign_id>/campaign.json"
  deletion_protection = false

  external_data_configuration {
    autodetect            = false
    source_format         = "NEWLINE_DELIMITED_JSON"
    ignore_unknown_values = true
    source_uris           = ["gs://${google_storage_bucket.campaigns.name}/campaigns/*/index.json"]

    schema = jsonencode([
      { name = "campaign_id", type = "STRING", mode = "NULLABLE", description = "CMP-<branch>-<yyyymmdd>-<code>" },
      { name = "branch_id", type = "STRING", mode = "NULLABLE" },
      { name = "branch_name", type = "STRING", mode = "NULLABLE" },
      { name = "city", type = "STRING", mode = "NULLABLE" },
      { name = "region_group", type = "STRING", mode = "NULLABLE" },
      { name = "business_division", type = "STRING", mode = "NULLABLE" },
      { name = "stage", type = "STRING", mode = "NULLABLE", description = "intake|filed|ideas_ready|idea_selected|copy_drafted|rendered|approved" },
      { name = "status", type = "STRING", mode = "NULLABLE", description = "draft|approved" },
      { name = "objective", type = "STRING", mode = "NULLABLE" },
      { name = "audience", type = "STRING", mode = "NULLABLE" },
      { name = "timing", type = "STRING", mode = "NULLABLE" },
      { name = "destination", type = "STRING", mode = "NULLABLE" },
      { name = "product_name", type = "STRING", mode = "NULLABLE" },
      { name = "idea_title", type = "STRING", mode = "NULLABLE" },
      { name = "formats", type = "STRING", mode = "NULLABLE", description = "Comma-separated list of formats" },
      { name = "asset_count", type = "INTEGER", mode = "NULLABLE" },
      { name = "created_by", type = "STRING", mode = "NULLABLE" },
      { name = "requester_name", type = "STRING", mode = "NULLABLE" },
      { name = "created_at", type = "STRING", mode = "NULLABLE", description = "ISO-8601 UTC" },
      { name = "updated_at", type = "STRING", mode = "NULLABLE", description = "ISO-8601 UTC" },
      { name = "gcs_prefix", type = "STRING", mode = "NULLABLE" },
    ])
  }

  depends_on = [google_storage_bucket.campaigns]
}

resource "google_bigquery_table_iam_member" "agent_identity_marketing_studio_viewer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.marketing_studio.dataset_id
  table_id   = google_bigquery_table.campaigns_index.table_id
  role       = "roles/bigquery.dataViewer"
  member     = local.agent_identity_member
}

resource "google_bigquery_dataset_iam_member" "users_marketing_studio_viewer" {
  for_each = toset(concat(var.finance_agent_user_members, var.pilot_retail_user_members))

  project    = var.project_id
  dataset_id = google_bigquery_dataset.marketing_studio.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value
}

resource "google_storage_bucket_iam_member" "users_campaigns_bucket_viewer" {
  for_each = toset(concat(var.finance_agent_user_members, var.pilot_retail_user_members))

  bucket = google_storage_bucket.campaigns.name
  role   = "roles/storage.objectViewer"
  member = each.value
}
