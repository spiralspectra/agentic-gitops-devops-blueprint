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
-- PII-free, RLS-scoped customer <-> booking bridge, applied by
-- sync_lakehouse_to_bq.py (templated: {project}, {dataset}).
--
-- `customermaster` links customers to bookings through repeated `AllBookingRefs`
-- and contains raw PII (names, contact details) that analytical tools should never
-- read directly. This authorized view exposes resolved (customer_hash, booking_reference)
-- pairs passing identity-confidence threshold (COALESCE(confidence_score, 500) >= 425)
-- plus marketing consent and order count flags, pseudonymizing customer IDs with SHA-256
-- and filtering through `v_operations` so 4-tier SESSION_USER() RLS is enforced.
CREATE OR REPLACE VIEW `{project}.{dataset}.v_finance_customer_bridge`
(
  customer_hash OPTIONS(description="SHA-256 pseudonymized customer identifier derived via TO_HEX(SHA256(CAST(c.CustomerID AS STRING))). Joins to pseudonymized customermosaicdemographics."),
  booking_reference OPTIONS(description="A booking made by this customer within caller's 4-tier RLS scope. Joins to v_operations.BookingReference and v_finance_transactions.booking_reference."),
  confidence_score OPTIONS(description="Identity-resolution confidence of the customer record; rows with COALESCE(confidence_score, 500) >= 425 are included."),
  customer_source OPTIONS(description="Source channel or system where customer record was captured."),
  customer_booking_count OPTIONS(description="Total count of booking references linked to this customer entity across history: > 1 indicates repeat customer."),
  mailing_allowed OPTIONS(description="Non-PII email communication consent flag from customermaster.MailingAllowed."),
  text_messaging OPTIONS(description="Non-PII SMS communication consent flag from customermaster.TextMessaging."),
  historical_fx_order_count OPTIONS(description="Count of historical ancillary foreign currency transactions linked to customer.")
)
OPTIONS(
  description="PII-free, 4-tier RLS-enforced bridge from pseudonymized customers to booking references (via customermaster.AllBookingRefs, COALESCE(confidence_score, 500) >= 425, scoped to v_operations)."
)
AS
SELECT
  TO_HEX(SHA256(CAST(c.CustomerID AS STRING))) AS customer_hash,
  ref                                          AS booking_reference,
  c.confidence_score                            AS confidence_score,
  c.source                                      AS customer_source,
  ARRAY_LENGTH(c.AllBookingRefs)                AS customer_booking_count,
  c.MailingAllowed                              AS mailing_allowed,
  c.TextMessaging                               AS text_messaging,
  ARRAY_LENGTH(c.AllFXOrders)                   AS historical_fx_order_count
FROM `{project}.{dataset}.customermaster` c
CROSS JOIN UNNEST(c.AllBookingRefs) AS ref
WHERE COALESCE(c.confidence_score, 500) >= 425
  AND EXISTS (
    SELECT 1
    FROM `{project}.{dataset}.v_operations` b
    WHERE b.BookingReference = ref
  );
