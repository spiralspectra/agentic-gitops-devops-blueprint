# Executive Pack SQL Queries & Variance Formulas

## 1. Executive Trading Summary by Division

```sql
SELECT
  division,
  COUNT(DISTINCT transaction_id) AS total_transactions,
  ROUND(SUM(gross_sales_amount), 2) AS gross_sales,
  ROUND(SUM(margin_amount), 2) AS net_margin,
  ROUND(SAFE_DIVIDE(SUM(margin_amount), SUM(gross_sales_amount)) * 100, 2) AS margin_pct,
  ROUND(SUM(discount_amount), 2) AS discount_total,
  ROUND(SAFE_DIVIDE(SUM(gross_sales_amount), COUNT(DISTINCT transaction_id)), 2) AS average_order_value
FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_transactions`
WHERE is_cancelled = FALSE
  AND transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY division
ORDER BY net_margin DESC;
```

## 2. Period-over-Period Variance & Margin Bridge

Decomposition of Margin Movement between Period A (Prior) and Period B (Current):

$$\Delta \text{Margin} = \text{Volume Effect} + \text{Mix Effect} + \text{Rate Effect}$$

```sql
WITH period_metrics AS (
  SELECT
    division,
    CASE 
      WHEN transaction_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE() THEN 'Current'
      WHEN transaction_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY) AND DATE_SUB(CURRENT_DATE(), INTERVAL 31 DAY) THEN 'Prior'
    END AS period,
    COUNT(DISTINCT transaction_id) AS orders,
    SUM(gross_sales_amount) AS sales,
    SUM(margin_amount) AS margin
  FROM `projects/your-gcp-project-id/datasets/enterprise_lakehouse/tables/v_finance_transactions`
  WHERE is_cancelled = FALSE
    AND transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  GROUP BY division, period
  HAVING period IS NOT NULL
)
SELECT
  division,
  period,
  orders,
  ROUND(sales, 2) AS sales,
  ROUND(margin, 2) AS margin,
  ROUND(SAFE_DIVIDE(margin, sales) * 100, 2) AS margin_pct
FROM period_metrics
ORDER BY division, period DESC;
```
