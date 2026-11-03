# Architecture & Workflow Diagrams

This directory contains production-grade architecture and workflow diagrams for the **Agentic GitOps & DevOps Blueprint**:

* `dev-gitops-workflow.svg` (and `.png` export): Illustrates the end-to-end developer and multi-agent workflow — developer workstation and ADC onboarding, GitHub Project v2 Kanban issue claims, isolated `git worktree` multi-agent parallel development, and the keyless GitHub Actions GitOps pipeline (`pr_checks.yaml` → `release.yaml`).
* `gcp-architecture.svg` (and `.png` export): Shows the production Google Cloud runtime and delivery architecture spanning all 4 deployment archetypes:
  1. Vertex AI Agent Engine (`agents/starter_agent/`) with `gemini-2.5-flash` router and `gemini-2.5-pro` pillar sub-agents.
  2. Managed Off-the-Shelf Agent Configuration-as-Code (`finance-agent/`).
  3. Interactive A2UI Frontend on Cloud Run behind Global HTTPS LB, Cloud Armor, and IAP (`a2ui-iframe/` or `frontend/`).
  4. Local Desktop Agent Extension (`gemini-spark-desktop/`).
  Plus BigQuery 4-Tier RLS Authorized Views (`SESSION_USER()`), Dataplex Knowledge Catalog, Spanner Property Graph, and continuous telemetry (Cloud Logging, Trace, Monitoring SLOs).
* `desktop-spark-architecture.svg` (and `.png` export): Visualizes the macOS Desktop Agent Extension (Spark) running inside the macOS Seatbelt sandbox with credentials in macOS Keychain, interfacing via loopback MCP to federated SaaS connectors and hosted Google Cloud MCP endpoints (`dataplex.googleapis.com/mcp` and `bigquery.googleapis.com/mcp`).

## Regenerating the Diagrams

All diagrams are generated using Python scripts with official Google Cloud product icons and Simple Icons brand marks:

```bash
# Regenerate SVG and 2x high-resolution PNG
python3 docs/architecture/build_dev_gitops_diagram.py --png
python3 docs/architecture/build_architecture_diagram.py --png
python3 docs/architecture/build_desktop_spark_diagram.py --png
```

PNG export uses headless Google Chrome / Chromium available on the local workstation or CI runner.
