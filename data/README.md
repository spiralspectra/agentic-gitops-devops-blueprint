# Synthetic Data & Zero-Trust View Guidelines

This directory contains database view templates and synthetic mock data schemas.

## Zero-Trust Authorized View Pattern (`data/views/`)
The reference SQL template in `data/views/10_v_authorized_records.sql` demonstrates the 4-tier row-level security pattern querying caller session identity against `user_entitlements`:
1. **Case and Whitespace Normalization**: Uses `LOWER(TRIM(SESSION_USER()))` matching normalized emails in `user_entitlements`.
2. **Blank String Guard**: Guarantees non-empty identity with `NULLIF(TRIM(...), '')`.
3. **Fan-out Prevention**: Evaluates permissions via `WHERE EXISTS (...)` against `user_entitlements` instead of `INNER JOIN` to guarantee zero record duplication.
4. **Strict Projection**: Never projects PII or raw authentication secrets.

## Synthetic Fixture Guidelines
- Never store or commit real customer or employee PII.
- Generate deterministic test records using synthetic UUIDs and realistic dummy values.
