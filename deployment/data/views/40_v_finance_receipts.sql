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
-- Payment-grain view over the row-level-secured `v_operations` view, applied by
-- sync_lakehouse_to_bq.py (templated: {project}, {dataset}).
--
-- One row per receipt / refund line (UNNEST of bookings.Receipts) with the
-- booking's selling-branch hierarchy repeated on every row, so cash, payment-
-- method mix, merchant-fee and refund questions can be answered without the
-- NL2SQL consumer having to UNNEST an ARRAY<STRUCT> itself (and without the
-- fan-out risk of summing booking-level measures alongside receipt lines:
-- this view deliberately carries NO booking-level money columns).
--
-- Security: built on `v_operations`, so 4-tier SESSION_USER() RLS applies.
CREATE OR REPLACE VIEW `{project}.{dataset}.v_finance_receipts`
(
  booking_reference OPTIONS(description="Booking the receipt belongs to. Join key to v_finance_transactions.booking_reference."),
  receipt_ref OPTIONS(description="Receipt line reference (BookingReceiptRef)."),
  receipt_date OPTIONS(description="Date the money was received or refunded."),
  receipt_month OPTIONS(description="First day of the receipt month."),
  receipt_type OPTIONS(description="'Receipt' = money in from the customer, 'Refund' = money returned to the customer, 'Unknown' = not classified."),
  payment_method OPTIONS(description="Payment method as recorded on the receipt."),
  payment_method_group OPTIONS(description="Payment method grouped: Card, Direct Debit, Cash, Bank Transfer, Trade/Other."),
  amount_gbp OPTIONS(description="Receipt amount in GBP; positive for receipts, NEGATIVE for refunds. SUM(amount_gbp) = net cash received."),
  merchant_fee_gbp OPTIONS(description="Card acquirer / merchant fee charged on the receipt in GBP (cost of taking payment)."),
  handling_fee_gbp OPTIONS(description="Handling fee charged to the customer on the receipt in GBP."),
  booking_credit_gbp OPTIONS(description="Booking credit applied on the receipt in GBP."),
  is_banked OPTIONS(description="TRUE when the receipt has been banked (BankedIndicator = 'Y')."),
  receipted_branch OPTIONS(description="Branch that processed the payment (may differ from selling branch)."),
  is_refund OPTIONS(description="TRUE when receipt_type = 'Refund'."),
  booking_date OPTIONS(description="Booking (sale) date of parent transaction."),
  departure_date OPTIONS(description="Departure date of parent transaction."),
  is_cancelled OPTIONS(description="TRUE when the parent booking is cancelled."),
  division OPTIONS(description="Business division of selling branch."),
  region_group OPTIONS(description="Regional group of selling branch."),
  branch_id OPTIONS(description="Selling branch identifier."),
  branch_name OPTIONS(description="Selling branch name.")
)
OPTIONS(
  description="Payment-grain, row-level-secured view: one row per customer receipt or refund line (from bookings.Receipts) in GBP, with payment method, merchant fees and parent branch hierarchy. Use for cash collected, payment-method mix, fee analysis and refund audits."
)
AS
SELECT
  b.BookingReference                                   AS booking_reference,
  r.BookingReceiptRef                                  AS receipt_ref,
  r.ReceiptDate                                        AS receipt_date,
  DATE_TRUNC(r.ReceiptDate, MONTH)                     AS receipt_month,
  CASE r.ReceiptRefund WHEN 'Receipt' THEN 'Receipt' WHEN 'Refund' THEN 'Refund' ELSE 'Unknown' END AS receipt_type,
  r.Description                                        AS payment_method,
  CASE
    WHEN REGEXP_CONTAINS(UPPER(COALESCE(r.Description, '')), r'VISA|MASTERCARD|AMERICAN EXPRESS|AMEX|MAESTRO|CARD') THEN 'Card'
    WHEN REGEXP_CONTAINS(UPPER(COALESCE(r.Description, '')), r'DIRECT DEBIT') THEN 'Direct Debit'
    WHEN UPPER(COALESCE(r.Description, '')) = 'CASH' THEN 'Cash'
    WHEN REGEXP_CONTAINS(UPPER(COALESCE(r.Description, '')), r'BANK|BACS|GIRO|TRANSFER') THEN 'Bank Transfer'
    ELSE 'Trade/Other'
  END                                                  AS payment_method_group,
  CAST(r.Amount AS FLOAT64)                            AS amount_gbp,
  CAST(r.MerchantFee AS FLOAT64)                       AS merchant_fee_gbp,
  CAST(r.HandlingFee AS FLOAT64)                       AS handling_fee_gbp,
  CAST(r.BookingCredit AS FLOAT64)                     AS booking_credit_gbp,
  (r.BankedIndicator = 'Y')                            AS is_banked,
  r.ReceiptedBranch                                    AS receipted_branch,
  (r.ReceiptRefund = 'Refund')                         AS is_refund,
  b.BookingDate                                        AS booking_date,
  b.DepartureDate                                      AS departure_date,
  (b.Cancelled = 'Y')                                  AS is_cancelled,
  b.SellingBranch.BranchBusinessDivision               AS division,
  b.SellingBranch.BranchGroup                          AS region_group,
  b.SaleBranchID                                       AS branch_id,
  b.SellingBranch.BranchName                           AS branch_name
FROM `{project}.{dataset}.v_operations` b
CROSS JOIN UNNEST(b.Receipts) AS r;
