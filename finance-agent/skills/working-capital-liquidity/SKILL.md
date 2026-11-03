---
name: working-capital-liquidity
description: Cash flow liquidity forecasting, balance-due receivable ageing ladders, vendor counterparty concentration, and foreign currency exposure analysis.
version: 1.0.0
---

# Working Capital & Liquidity Forecasting

Evaluates cash flow velocity, accounts receivable ageing, supplier counterparty credit risk, and FX exposure.

## Workflow

1. **Calculate Receivables Ageing Ladder**:
   - Bucket outstanding balances from `v_finance_transactions` into Current (0-30d), 31-60d, 61-90d, and >90d tranches.
   - Flag collections at high risk of bad debt or default.
   - Reference detailed query structures in `queries.md`.
2. **Project Short-Term Cash Velocity**:
   - Model cash receipts by comparing forward maturity dates against historical settlement timing.
3. **Assess Counterparty Concentration Risk**:
   - Rank top vendors by commercial volume and outstanding commitments.
   - Enforce concentration limits to ensure no single counterparty represents disproportionate liquidity exposure.
4. **Audit Foreign Currency Exposure**:
   - Segment commitments by settlement currency (`vendor_currency`).
   - Highlight unhedged non-base currency exposures.

## Available References

- `queries.md` — Certified SQL queries for receivables ageing and counterparty concentration analysis.
