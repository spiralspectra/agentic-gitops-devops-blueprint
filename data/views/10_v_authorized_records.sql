-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- 4-Tier Zero-Trust BigQuery Authorized View Pattern
-- Enforces row-level entitlements and column masking based on caller SESSION_USER().
--
-- Architecture Pillars:
--   1. Strict Normalization: LOWER(TRIM(SESSION_USER())) matches entitlement entries.
--   2. Blank String Guard: NULLIF(TRIM(...), '') prevents unauthenticated fallback matches.
--   3. Fan-out Prevention: WHERE EXISTS (...) instead of INNER JOIN prevents duplicate rows.
--   4. Column Projection: PII and sensitive internal credentials excluded from view.

CREATE OR REPLACE VIEW `your-gcp-project-id.my_agent_service_data.v_authorized_records` AS
SELECT
  r.record_id,
  r.tenant_id,
  r.department_code,
  r.transaction_timestamp,
  r.item_count,
  r.total_amount_cents,
  r.status
FROM
  `your-gcp-project-id.my_agent_service_data.raw_records` AS r
WHERE
  EXISTS (
    SELECT 1
    FROM
      `your-gcp-project-id.my_agent_service_data.user_entitlements` AS e
    WHERE
      e.authorized_user_email = LOWER(TRIM(SESSION_USER()))
      AND e.authorized_user_email IS NOT NULL
      AND NULLIF(TRIM(e.authorized_user_email), '') IS NOT NULL
      AND (
        e.is_global_admin = TRUE
        OR e.tenant_id = r.tenant_id
      )
  );
