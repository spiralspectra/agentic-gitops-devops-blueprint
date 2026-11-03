-- Copyright 2026 The Project Contributors
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- Row-level-secured operations view over `bookings`, applied by sync_lakehouse_to_bq.py
-- (templated: {project}, {dataset}). Every transaction a caller may see is checked
-- against that caller's `user_entitlements` rows on SESSION_USER() using EXISTS
-- (preventing row fan-out when a user holds multiple scope rows) and ignoring
-- blank identities; the 4 tiers match the RLS policy on `bookings`.
-- Remuneration (`Commission`) is excluded via EXCEPT(Commission) for
-- defense-in-depth; Finance queries `v_finance_transactions` instead.
CREATE OR REPLACE VIEW `{project}.{dataset}.v_operations` AS
WITH caller_entitlements AS (
  SELECT ARRAY_AGG(STRUCT(
    e.role,
    e.branch_id,
    e.username,
    e.region_group,
    e.division
  )) AS scopes
  FROM `{project}.{dataset}.user_entitlements` e
  WHERE LOWER(NULLIF(TRIM(e.wif_subject), '')) = LOWER(SESSION_USER())
     OR LOWER(NULLIF(TRIM(e.user_email), '')) = LOWER(SESSION_USER())
)
SELECT b.* EXCEPT(Commission)
FROM `{project}.{dataset}.bookings` b
CROSS JOIN caller_entitlements ce
WHERE EXISTS (
  SELECT 1
  FROM UNNEST(ce.scopes) AS e
  WHERE (
          e.role = 'BRANCH_STAFF'
          AND (e.branch_id = '*' OR b.SaleBranchID = e.branch_id)
          AND (e.username = '*' OR b.Username = e.username)
        )
     OR (
          e.role = 'BRANCH_MANAGER'
          AND (e.branch_id = '*' OR b.SaleBranchID = e.branch_id)
        )
     OR (
          e.role = 'REGIONAL_MANAGER'
          AND (UPPER(TRIM(e.region_group)) = 'ALL' OR b.SellingBranch.BranchGroup = e.region_group)
        )
     OR (
          e.role = 'DIVISIONAL_HEAD'
          AND (UPPER(TRIM(e.division)) = 'ALL' OR b.SellingBranch.BranchBusinessDivision = e.division)
        )
);
