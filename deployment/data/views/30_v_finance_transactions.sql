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
-- Finance-grain view over raw `bookings` with the same caller_entitlements
-- 4-tier RLS predicate as v_operations, applied by
-- sync_lakehouse_to_bq.py (templated: {project}, {dataset}).
--
-- Purpose: give the Financial Services / FP&A agents and other NL2SQL consumers
-- ONE flat, well-described row per transaction with every financial measure
-- already typed as FLOAT64 GBP and the nested STRUCT dimensions (SellingBranch,
-- DestinationType, DeparturePoint) and supplier master flattened.
--
-- Security: enforces 4-tier SESSION_USER() RLS; the base `bookings` table
-- additionally carries the row access policy. A caller with no entitlement row
-- sees zero rows, not an error.
CREATE OR REPLACE VIEW `{project}.{dataset}.v_finance_transactions`
(
  booking_reference OPTIONS(description="Unique transaction reference (one row per booking). Join key to v_finance_receipts.booking_reference and v_finance_customer_bridge.booking_reference."),
  booking_date OPTIONS(description="Date the transaction was recorded (sale date). Use for trading and sales-period analysis."),
  booking_month OPTIONS(description="First day of the transaction month, derived from booking_date."),
  booking_week OPTIONS(description="Monday of the ISO week of booking_date."),
  departure_date OPTIONS(description="Service departure date. Use for forward-book, revenue-recognition-on-departure and seasonality analysis."),
  departure_month OPTIONS(description="First day of the departure month, derived from departure_date."),
  return_date OPTIONS(description="Service return date."),
  duration_nights OPTIONS(description="Duration in nights/days as recorded on the booking."),
  lead_time_days OPTIONS(description="Days between booking_date and departure_date (lead time)."),
  balance_due_date OPTIONS(description="Date the remaining balance must be settled by. Use with outstanding_gbp for receivables ageing and cash-due forecasting."),
  is_cancelled OPTIONS(description="TRUE when the booking is cancelled (Cancelled = 'Y'). Exclude cancelled transactions from revenue and forward-book totals unless analyzing cancellation rates."),
  division OPTIONS(description="Business division of the selling branch (e.g. RETAIL, COMMERCIAL, DIRECT, WEB)."),
  sub_division OPTIONS(description="Sub-division of the selling branch."),
  region_group OPTIONS(description="Regional group of the selling branch. Corresponds to the Regional Manager tier."),
  branch_id OPTIONS(description="Selling branch identifier (SaleBranchID). Branch Manager / Branch Staff tier."),
  branch_name OPTIONS(description="Selling branch name."),
  branch_city OPTIONS(description="Selling branch city."),
  branch_county OPTIONS(description="Selling branch county/state."),
  branch_has_forex OPTIONS(description="'Yes' when the selling branch has a currency exchange desk."),
  buying_branch_id OPTIONS(description="Branch that fulfilled the product when different from the selling branch."),
  consultant_username OPTIONS(description="System username of the consultant who recorded the transaction."),
  consultant_name OPTIONS(description="Display name of the consultant/agent who recorded the transaction."),
  supplier_key OPTIONS(description="Surrogate supplier key (AE_SupplierKey)."),
  supplier_id OPTIONS(description="Supplier identifier code."),
  supplier_name OPTIONS(description="Supplier or partner provider name."),
  supplier_currency OPTIONS(description="Currency the supplier is settled in (blank/NULL indicates GBP). Non-GBP indicates FX exposure on cost of sale."),
  supplier_payment_terms OPTIONS(description="Supplier payment terms code from supplier master."),
  is_in_house_supplier OPTIONS(description="TRUE when the supplier is an enterprise in-house brand."),
  destination_category OPTIONS(description="Destination category (e.g., Short Haul, Long Haul, Specialized, Domestic)."),
  destination_sector OPTIONS(description="Destination sector geographical region."),
  destination OPTIONS(description="Destination name as classified in corporate taxonomy."),
  destination_country OPTIONS(description="Destination country."),
  departure_point OPTIONS(description="Departure terminal or port name."),
  departure_point_type OPTIONS(description="Departure point type (airport, rail, port)."),
  passengers OPTIONS(description="Total passengers/parties on the transaction."),
  adults OPTIONS(description="Number of adults."),
  children OPTIONS(description="Number of children."),
  seniors OPTIONS(description="Number of seniors."),
  source_code OPTIONS(description="Marketing or enquiry source code."),
  trading_name OPTIONS(description="Trading brand name the transaction was completed under."),
  bonding_type OPTIONS(description="Consumer protection bonding type applicable to the transaction."),
  regulatory_license OPTIONS(description="Regulatory license identifier if applicable."),
  industry_association_id OPTIONS(description="Industry association registration identifier if applicable."),
  is_direct_debit OPTIONS(description="TRUE when the transaction is paid via direct debit/recurring instalments."),
  is_po_booking OPTIONS(description="TRUE when transaction was billed against a purchase order."),
  is_surprise_booking OPTIONS(description="TRUE when flagged as a gift or surprise booking."),
  gross_sales_gbp OPTIONS(description="Gross selling value in GBP = Total Transaction Value (TTV)."),
  profit_gbp OPTIONS(description="Enterprise gross profit / commercial margin earned on the booking in GBP. Margin % = profit_gbp / gross_sales_gbp."),
  commission_gbp OPTIONS(description="Commission earned by individual consultant / agent in GBP. Colleague remuneration, distinct from gross margin."),
  discount_gbp OPTIONS(description="Discount given to customer in GBP, recorded as a negative number (0 when none)."),
  margin_pct OPTIONS(description="Transaction margin as a ratio: profit_gbp / gross_sales_gbp (NULL when gross is 0)."),
  deposit_gbp OPTIONS(description="Deposit paid at transaction creation in GBP."),
  total_paid_gbp OPTIONS(description="Total funds received from customer to date in GBP."),
  outstanding_gbp OPTIONS(description="Remaining balance owed by customer in GBP."),
  card_paid_gbp OPTIONS(description="Amount settled by credit/debit card in GBP."),
  cash_paid_gbp OPTIONS(description="Amount settled in cash in GBP."),
  cheque_paid_gbp OPTIONS(description="Amount settled by cheque in GBP."),
  direct_paid_gbp OPTIONS(description="Amount settled by direct bank transfer in GBP."),
  has_flight OPTIONS(description="TRUE when booking includes flight elements."),
  has_hotel OPTIONS(description="TRUE when booking includes accommodation elements."),
  has_cruise OPTIONS(description="TRUE when booking includes maritime cruise elements."),
  has_insurance OPTIONS(description="TRUE when protection/insurance policy was attached."),
  insurance_gross_gbp OPTIONS(description="Gross policy premium attached in GBP."),
  insurance_ipt_gbp OPTIONS(description="Insurance tax value within premium in GBP."),
  element_count OPTIONS(description="Total number of booked package components."),
  original_booking_datetime OPTIONS(description="Timestamp transaction record was created."),
  last_modified_datetime OPTIONS(description="Timestamp transaction record was last modified.")
)
OPTIONS(
  description="Finance-grain, flat, row-level-secured view: one row per enterprise booking with GBP financial measures (TTV, profit/margin, commission, discount, deposits, balances), branch hierarchy, supplier and destination dimensions. Enforces 4-tier SESSION_USER() RLS over bookings."
)
AS
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
SELECT
  b.BookingReference                                   AS booking_reference,
  b.BookingDate                                        AS booking_date,
  DATE_TRUNC(b.BookingDate, MONTH)                     AS booking_month,
  DATE_TRUNC(b.BookingDate, ISOWEEK)                   AS booking_week,
  b.DepartureDate                                      AS departure_date,
  DATE_TRUNC(b.DepartureDate, MONTH)                   AS departure_month,
  b.ReturnDate                                         AS return_date,
  b.Duration                                           AS duration_nights,
  DATE_DIFF(b.DepartureDate, b.BookingDate, DAY)       AS lead_time_days,
  b.BalanceDue                                         AS balance_due_date,
  (b.Cancelled = 'Y')                                  AS is_cancelled,
  b.SellingBranch.BranchBusinessDivision               AS division,
  b.SellingBranch.BranchSubDivision                    AS sub_division,
  b.SellingBranch.BranchGroup                          AS region_group,
  b.SaleBranchID                                       AS branch_id,
  b.SellingBranch.BranchName                           AS branch_name,
  b.SellingBranch.City                                 AS branch_city,
  b.SellingBranch.County                               AS branch_county,
  b.SellingBranch.HasForex                             AS branch_has_forex,
  b.BuyingBranchID                                     AS buying_branch_id,
  b.Username                                           AS consultant_username,
  b.AgentName                                          AS consultant_name,
  b.AE_SupplierKey                                     AS supplier_key,
  s.SupplierID                                         AS supplier_id,
  s.SupplierName                                       AS supplier_name,
  NULLIF(TRIM(s.SupplierCurrencyCode), '')             AS supplier_currency,
  s.SupplierPaymentTermsCode                           AS supplier_payment_terms,
  COALESCE(REGEXP_CONTAINS(UPPER(s.SupplierName), r'^ENTERPRISE |DIRECT'), FALSE) AS is_in_house_supplier,
  b.DestinationType.DestinationCategory                AS destination_category,
  b.DestinationType.DestinationSector                  AS destination_sector,
  b.DestinationType.Destination                        AS destination,
  b.TravelTek_DestinationCountry                       AS destination_country,
  b.DeparturePoint.DeparturePointName                  AS departure_point,
  b.DeparturePoint.DeparturePointType                  AS departure_point_type,
  b.Passengers                                         AS passengers,
  b.Adults                                             AS adults,
  b.Children                                           AS children,
  b.Seniors                                            AS seniors,
  b.SourceCode                                         AS source_code,
  b.TradingName                                        AS trading_name,
  b.BondingType                                        AS bonding_type,
  b.RegulatoryLicense                                  AS regulatory_license,
  b.IndustryAssociationID                              AS industry_association_id,
  (b.IsPaidByDirectDebit = 'Yes')                      AS is_direct_debit,
  (b.POBooking = 'Y')                                  AS is_po_booking,
  (b.SurpriseBooking = 'Y')                            AS is_surprise_booking,
  CAST(b.GrossPrice AS FLOAT64)                        AS gross_sales_gbp,
  CAST(b.Profit AS FLOAT64)                            AS profit_gbp,
  CAST(b.Commission AS FLOAT64)                        AS commission_gbp,
  CAST(b.Discount AS FLOAT64)                          AS discount_gbp,
  SAFE_DIVIDE(CAST(b.Profit AS FLOAT64), NULLIF(CAST(b.GrossPrice AS FLOAT64), 0)) AS margin_pct,
  CAST(b.Deposit AS FLOAT64)                           AS deposit_gbp,
  CAST(b.TotalPayment AS FLOAT64)                      AS total_paid_gbp,
  CAST(b.Outstanding AS FLOAT64)                       AS outstanding_gbp,
  CAST(b.CardPayment AS FLOAT64)                       AS card_paid_gbp,
  CAST(b.CashPayment AS FLOAT64)                       AS cash_paid_gbp,
  CAST(b.ChequePayment AS FLOAT64)                     AS cheque_paid_gbp,
  CAST(b.DirectPayment AS FLOAT64)                     AS direct_paid_gbp,
  (ARRAY_LENGTH(b.FlightDetails) > 0 OR ARRAY_LENGTH(b.FlightOnlyDetails) > 0) AS has_flight,
  (ARRAY_LENGTH(b.HotelDetails) > 0 OR ARRAY_LENGTH(b.HotelOnlyDetails) > 0)   AS has_hotel,
  (ARRAY_LENGTH(b.CruiseDetails) > 0)                  AS has_cruise,
  (ARRAY_LENGTH(b.InsuranceDetails) > 0)               AS has_insurance,
  (SELECT SUM(CAST(i.GrossPolicyPrice AS FLOAT64)) FROM UNNEST(b.InsuranceDetails) i) AS insurance_gross_gbp,
  (SELECT SUM(CAST(i.IPTValue AS FLOAT64)) FROM UNNEST(b.InsuranceDetails) i)         AS insurance_ipt_gbp,
  (ARRAY_LENGTH(b.FlightDetails) + ARRAY_LENGTH(b.HotelDetails) + ARRAY_LENGTH(b.CruiseDetails)
   + ARRAY_LENGTH(b.HotelOnlyDetails) + ARRAY_LENGTH(b.FlightOnlyDetails) + ARRAY_LENGTH(b.InsuranceDetails)
   + ARRAY_LENGTH(b.AttractionsEventsDetails) + ARRAY_LENGTH(b.TransferDetails) + ARRAY_LENGTH(b.MiscellaneousDetails)
   + ARRAY_LENGTH(b.CarParkDetails) + ARRAY_LENGTH(b.CarHireDetails) + ARRAY_LENGTH(b.CoachDetails)) AS element_count,
  b.OriginalBookingDatetime                            AS original_booking_datetime,
  b.LastModifiedDateTime                               AS last_modified_datetime
FROM `{project}.{dataset}.bookings` b
CROSS JOIN caller_entitlements ce
LEFT JOIN `{project}.{dataset}.supplier` s
  ON b.AE_SupplierKey = s.SupplierKey
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
