# Working Capital & Liquidity Forecasting SQL Queries

## 1. Accounts Receivable Ageing & Balance Due Ladder

```sql
SELECT
  CASE
    WHEN DATE_DIFF(CURRENT_DATE(), transaction_date, DAY) <= 30 THEN '01. Current (0-30 Days)'
    WHEN DATE_DIFF(CURRENT_DATE(), transaction_date, DAY) BETWEEN 31 AND 60 THEN '02. 31-60 Days'
    WHEN DATE_DIFF(CURRENT_DATE(), transaction_date, DAY) BETWEEN 61 AND 90 THEN '03. 61-90 Days'
    ELSE '04. Over 90 Days'
  END AS ageing_bracket,
  COUNT(DISTINCT transaction_id) AS open_transactions,
  ROUND(SUM(outstanding_balance), 2) AS total_uncollected_balance,
  ROUND(SAFE_DIVIDE(SUM(outstanding_balance), SUM(SUM(outstanding_balance)) OVER ()) * 100, 2) AS pct_of_total_ar
FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_transactions`
WHERE is_cancelled = FALSE
  AND outstanding_balance > 0
GROUP BY ageing_bracket
ORDER BY ageing_bracket;
```

## 2. Vendor Counterparty Concentration & Foreign Currency Exposure

```sql
SELECT
  vendor_id,
  vendor_name,
  COALESCE(vendor_currency, 'USD') AS settlement_currency,
  COUNT(DISTINCT transaction_id) AS transactions,
  ROUND(SUM(gross_sales_amount), 2) AS total_commercial_volume,
  ROUND(SUM(margin_amount), 2) AS retained_margin,
  ROUND(SAFE_DIVIDE(SUM(gross_sales_amount), SUM(SUM(gross_sales_amount)) OVER ()) * 100, 2) AS volume_share_pct
FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_transactions`
WHERE is_cancelled = FALSE
  AND transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY vendor_id, vendor_name, settlement_currency
ORDER BY total_commercial_volume DESC
LIMIT 20;
```
