---
name: executive-pack
description: Executive trading pack, P&L review, margin variance bridges, discount leakage, and period-over-period financial movements by division and product category.
version: 1.0.0
---

# Executive Financial Review & Margin Bridges

Produces executive-level financial reporting and performance packs for business leadership.

## Workflow

1. **Establish Reporting Period**:
   - Determine baseline and comparison windows (Month-to-Date, Quarter-to-Date, or Trailing 30/60/90 Days).
   - Filter `is_cancelled = FALSE` on `v_finance_transactions` to reflect true commercial operations.
2. **Execute Financial Aggregations**:
   - Compute Gross Sales ($TTV), Net Margin, Margin %, Total Orders, Average Order Value (AOV), and Discount Leakage.
   - Reference standard query templates in `queries.md`.
3. **Decompose Margin Bridges**:
   - Break down variance into Volume Effect, Price/Rate Effect, and Product/Division Mix Effect.
4. **Reconcile Totals**:
   - Run a top-level unsegmented query to verify that the sum of parts equals total published net margin.
5. **Format Executive Brief**:
   - Headline commercial performance.
   - 3-5 operational takeaways.
   - Structured performance table.

## Available References

- `queries.md` — Golden SQL queries for executive trading packs and margin bridge formulas.
