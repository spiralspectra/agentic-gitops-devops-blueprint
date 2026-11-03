# Local Desktop Extension — Workspace Governance & Execution Rules

1. **Host Sandboxing & Minimal Privilege:**
   - Execute under the macOS Seatbelt sandbox profile (`sandbox.json` / `sandbox.sb`).
   - Network egress is permitted strictly to Google Cloud API endpoints (`dataplex.googleapis.com`, `bigquery.googleapis.com`).
   - File system writes are restricted to the local workspace and designated temporary directories.

2. **Zero-Trust Token Management:**
   - Never store plain text authentication secrets, API keys, or service account keys in the workspace directory.
   - Credentials must be stored in and retrieved from the macOS Keychain (`security find-generic-password -s desktop-agent-gcp-token`) or ambient Application Default Credentials.

3. **Governed Data Access via Remote MCP Bridge:**
   - All lakehouse queries must route through the zero-dependency Python 3.9 MCP bridge (`desktop_agent_data_mcp.py`).
   - Read-only queries must target governed views (`v_operations`, `v_catalog_enriched`, `v_finance_transactions`).
   - Reconcile shift metrics against the Knowledge Catalog glossary.

4. **Zero-CDN Offline Canvas Output:**
   - All visual dashboards, timelines, and Gantt scorecards generated for the local workspace must be 100% self-contained HTML/SVG documents.
   - Do not link external CDNs (e.g. unpkg, cdnjs, Google Fonts). The output must render offline in sandboxed webviews.

5. **Sensitive Remuneration & Payroll Guardrail:**
   - Refuse any request to query, calculate, estimate, or reveal employee salaries, commission, bonuses, or payroll data.
   - Immediately decline such inquiries with a standard referral to Human Resources / Payroll management.
