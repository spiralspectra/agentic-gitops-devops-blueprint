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

# Google Cloud Knowledge Catalog — Context Set EntryGroup & Custom Aspect Types
# for Enterprise ADK Agents.
#
# Brownfield import blocks adopt pre-existing objects when adopt_existing = true.

import {
  for_each = local.adopt
  to       = google_dataplex_entry_group.enterprise_context_set
  id       = "projects/${var.project_id}/locations/${var.region}/entryGroups/enterprise-context-set"
}

import {
  for_each = local.adopt
  to       = google_dataplex_aspect_type.ontology_contract
  id       = "projects/${var.project_id}/locations/${var.region}/aspectTypes/ontology-contract"
}

import {
  for_each = local.adopt
  to       = google_dataplex_aspect_type.governance_rls
  id       = "projects/${var.project_id}/locations/${var.region}/aspectTypes/governance-rls"
}

import {
  for_each = local.adopt
  to       = google_dataplex_glossary.enterprise_glossary
  id       = "projects/${var.project_id}/locations/${var.region}/glossaries/enterprise-semantic-glossary"
}

resource "google_dataplex_entry_group" "enterprise_context_set" {
  project        = var.project_id
  location       = var.region
  entry_group_id = "enterprise-context-set"
  display_name   = "Enterprise Context Set"
  description    = "Curated Knowledge Catalog Context Set and Context Graph for Enterprise ADK Agents (Pillar 1 Productivity, Pillar 2 Personalisation, Pillar 3 Marketing Studio)."

  labels = {
    type       = "context-set"
    managed_by = "terraform"
    domain     = "enterprise-retail"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}

resource "google_dataplex_aspect_type" "ontology_contract" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "ontology-contract"
  display_name   = "Enterprise Ontology & Join Contract"
  description    = "Authoritative table grain, primary key, canonical SQL join paths, and anti-pattern rules."

  metadata_template = jsonencode({
    name = "EnterpriseOntologyContract"
    type = "record"
    recordFields = [
      {
        name        = "grain"
        type        = "string"
        index       = 1
        annotations = { displayName = "Row Grain" }
        constraints = { required = true }
      },
      {
        name        = "primary_key"
        type        = "string"
        index       = 2
        annotations = { displayName = "Primary Key" }
      },
      {
        name        = "business_key"
        type        = "string"
        index       = 3
        annotations = { displayName = "Business Key" }
      },
      {
        name        = "canonical_joins"
        type        = "string"
        index       = 4
        annotations = { displayName = "Canonical SQL Joins" }
      },
      {
        name        = "prohibited_anti_patterns"
        type        = "string"
        index       = 5
        annotations = { displayName = "Prohibited SQL Anti-Patterns" }
      }
    ]
  })

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}

resource "google_dataplex_aspect_type" "governance_rls" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "governance-rls"
  display_name   = "Enterprise Lineage & 4-Tier RLS Contract"
  description    = "Cross-cloud Unity Catalog lineage, Borderless Lakehouse federation target, and 4-tier RLS contract."

  metadata_template = jsonencode({
    name = "EnterpriseGovernanceRls"
    type = "record"
    recordFields = [
      {
        name        = "source_system"
        type        = "string"
        index       = 1
        annotations = { displayName = "Source System & Metastore" }
        constraints = { required = true }
      },
      {
        name        = "federation_architecture"
        type        = "string"
        index       = 2
        annotations = { displayName = "Federation Architecture" }
      },
      {
        name        = "rls_policy"
        type        = "string"
        index       = 3
        annotations = { displayName = "Row-Level Security Policy" }
      },
      {
        name        = "pii_masking"
        type        = "string"
        index       = 4
        annotations = { displayName = "PII Masking Rules" }
      }
    ]
  })

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}

resource "google_dataplex_glossary" "enterprise_glossary" {
  project      = var.project_id
  location     = var.region
  glossary_id  = "enterprise-semantic-glossary"
  display_name = "Enterprise Retail & Commercial Business Glossary"
  description  = "Canonical business terminology for Enterprise Retail (calendar Month-to-Date (MTD), 1WD report, Customer 360 confidence gate, industry compliance)."

  labels = {
    domain     = "enterprise-retail"
    managed_by = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.services]
}
