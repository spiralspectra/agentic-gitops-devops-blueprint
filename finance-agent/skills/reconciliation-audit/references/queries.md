# Transaction vs Receipt Reconciliation SQL Queries

## 1. Cash Settlement vs Invoiced Sales Reconciliation

```sql
WITH sales AS (
  SELECT
    transaction_id,
    unit_id,
    transaction_date,
    gross_sales_amount,
    outstanding_balance
  FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_transactions`
  WHERE is_cancelled = FALSE
    AND transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),
receipts AS (
  SELECT
    transaction_id,
    SUM(amount) AS total_cash_received,
    SUM(merchant_fee) AS total_merchant_fees
  FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_receipts`
  GROUP BY transaction_id
)
SELECT
  s.unit_id,
  COUNT(DISTINCT s.transaction_id) AS transaction_count,
  ROUND(SUM(s.gross_sales_amount), 2) AS billed_sales,
  ROUND(SUM(COALESCE(r.total_cash_received, 0)), 2) AS cash_collected,
  ROUND(SUM(s.outstanding_balance), 2) AS reported_outstanding,
  ROUND(SUM(s.gross_sales_amount - COALESCE(r.total_cash_received, 0)), 2) AS calculated_variance,
  ROUND(SUM(COALESCE(r.total_merchant_fees, 0)), 2) AS acquiring_costs
FROM sales s
LEFT JOIN receipts r ON s.transaction_id = r.transaction_id
GROUP BY s.unit_id
ORDER BY calculated_variance DESC;
```

## 2. Payment Method Mix and Merchant Fee Analysis

```sql
SELECT
  payment_method,
  receipt_type,
  COUNT(receipt_id) AS receipt_count,
  ROUND(SUM(amount), 2) AS net_cash_amount,
  ROUND(SUM(merchant_fee), 2) AS total_merchant_fees,
  ROUND(SAFE_DIVIDE(SUM(merchant_fee), SUM(amount)) * 100, 3) AS effective_fee_rate_pct
FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_receipts`
WHERE receipt_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY payment_method, receipt_type
ORDER BY net_cash_amount DESC;
```
