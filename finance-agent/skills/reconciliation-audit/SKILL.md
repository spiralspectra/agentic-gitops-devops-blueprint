---
name: reconciliation-audit
description: Transaction vs receipt audit, settlement reconciliation, payment method fee leakage, refund audits, and cash variance analysis.
version: 1.0.0
---

# Transaction & Cash Receipt Reconciliation Audit

Conducts financial reconciliation audits comparing billed sales against cash settlement logs.

## Workflow

1. **Pre-Aggregate Receipts by Transaction**:
   - Aggregate `v_finance_receipts` at the `transaction_id` level before joining with `v_finance_transactions` to avoid cartesian inflation.
   - Reference queries and join patterns in `queries.md`.
2. **Compute Variance & Unsettled Balances**:
   - Compare `gross_sales_amount` against sum of settled `amount`.
   - Calculate delta between ledger `outstanding_balance` and derived cash differential.
3. **Audit Merchant Fee Incurrence**:
   - Assess merchant fee leakage across card processors and payment rails.
   - Flag anomalies where acquiring fees exceed target thresholds.
4. **Identify Refund Spike Outliers**:
   - Group `v_finance_receipts` where `receipt_type = 'Refund'` to identify anomalous return patterns by business unit or vendor.

## Available References

- `queries.md` — Certified BigQuery SQL queries for transactional reconciliation and merchant fee audit.
