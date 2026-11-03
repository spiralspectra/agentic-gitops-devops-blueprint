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
-- Remediates `lakehouse_sharing.user_entitlements` so the 4-tier RLS model
-- operates per user role rather than treating every signed-in account (or the
-- shared Reasoning Engine runtime identity) as `DIVISIONAL_HEAD / ALL`.
--
-- Usage (substitute project/dataset if non-default, or run directly via bq):
--   bq query --project_id=PROJECT_ID --location=europe-west2 \
--     --use_legacy_sql=false < deployment/data/seed_pilot_entitlements.sql

BEGIN TRANSACTION;

-- 1. Remove blank wildcard row and unauthenticated identities so non-delegated calls
--    cannot view data via fallback.
DELETE FROM `lakehouse_sharing.user_entitlements`
WHERE TRIM(IFNULL(user_email, '')) = ''
   OR STARTS_WITH(TRIM(IFNULL(user_email, '')), 'principal://agents.global.')
   OR STARTS_WITH(TRIM(IFNULL(wif_subject, '')), 'principal://agents.global.');

-- 2. Ensure both CI and Deployer automation service accounts are entitled
--    for automated PR evaluations, post-deploy smoke tests, and view validation.
MERGE `lakehouse_sharing.user_entitlements` t
USING (
  SELECT 'enterprise-agent-ci@retail-enterprise-gemini.iam.gserviceaccount.com' AS email
  UNION ALL
  SELECT 'enterprise-agent-deployer@retail-enterprise-gemini.iam.gserviceaccount.com' AS email
) s
ON LOWER(TRIM(t.user_email)) = LOWER(TRIM(s.email))
WHEN MATCHED THEN
  UPDATE SET
    wif_subject  = s.email,
    role         = 'DIVISIONAL_HEAD',
    branch_id    = '*',
    username     = '*',
    region_group = 'ALL',
    division     = 'ALL'
WHEN NOT MATCHED THEN
  INSERT (user_email, wif_subject, role, branch_id, username, region_group, division)
  VALUES (s.email, s.email, 'DIVISIONAL_HEAD', '*', '*', 'ALL', 'ALL');

-- 3. Assign distinct 4-tier RLS scopes to pilot personas using verified entity keys
--    demonstrating strict row-level isolation instead of superadmin access:
--
--    Tier 1 (BRANCH_STAFF)     : staff.consultant@retail-pilot.example.com  -> Branch 0015, consultant JOF8 only
--    Tier 2 (BRANCH_MANAGER)   : branch.manager@retail-pilot.example.com    -> Branch 0015 (all branch consultants)
--    Tier 3 (REGIONAL_MANAGER) : regional.lead@retail-pilot.example.com     -> REGION NORTH branches
--    Tier 3 (REGIONAL_MANAGER) : west.regional@retail-pilot.example.com     -> REGION WEST branches
--    Tier 4 (DIVISIONAL_HEAD)  : retail.director@retail-pilot.example.com   -> RETAIL division only
--    Tier 4 (DIVISIONAL_HEAD)  : enterprise.exec@retail-pilot.example.com   -> ALL divisions
--    Tier 4 (EXEC / ADMIN)     : admin.auditor@retail-pilot.example.com     -> ALL divisions
MERGE `lakehouse_sharing.user_entitlements` t
USING (
  SELECT 'staff.consultant@retail-pilot.example.com'  AS user_email, 'BRANCH_STAFF'     AS role, '0015' AS branch_id, 'JOF8' AS username, 'REGION NORTH' AS region_group, 'RETAIL' AS division UNION ALL
  SELECT 'branch.manager@retail-pilot.example.com',   'BRANCH_MANAGER',   '0015', '*',    'REGION NORTH', 'RETAIL' UNION ALL
  SELECT 'regional.lead@retail-pilot.example.com',    'REGIONAL_MANAGER', '*',    '*',    'REGION NORTH', 'RETAIL' UNION ALL
  SELECT 'west.regional@retail-pilot.example.com',    'REGIONAL_MANAGER', '*',    '*',    'REGION WEST',  'RETAIL' UNION ALL
  SELECT 'retail.director@retail-pilot.example.com',  'DIVISIONAL_HEAD',  '*',    '*',    'ALL',          'RETAIL' UNION ALL
  SELECT 'enterprise.exec@retail-pilot.example.com',  'DIVISIONAL_HEAD',  '*',    '*',    'ALL',          'ALL'    UNION ALL
  SELECT 'admin.auditor@retail-pilot.example.com',    'DIVISIONAL_HEAD',  '*',    '*',    'ALL',          'ALL'
) s
ON LOWER(TRIM(t.user_email)) = LOWER(TRIM(s.user_email))
WHEN MATCHED THEN
  UPDATE SET
    wif_subject  = s.user_email,
    role         = s.role,
    branch_id    = s.branch_id,
    username     = s.username,
    region_group = s.region_group,
    division     = s.division
WHEN NOT MATCHED THEN
  INSERT (user_email, wif_subject, role, branch_id, username, region_group, division)
  VALUES (s.user_email, s.user_email, s.role, s.branch_id, s.username, s.region_group, s.division);

COMMIT TRANSACTION;
