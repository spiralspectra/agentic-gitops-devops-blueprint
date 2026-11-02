# Bootstrap New Project Prompt Templates

Use these copy-pasteable prompt templates to instruct any AI coding agent (Google Antigravity, Gemini CLI, Claude Code, Cursor) to scaffold a production GitOps & DevOps foundation into a target repository.

---

## Universal Bootstrap Prompt (For Any AI Agent)

```text
You are an expert Google Cloud and GitOps DevOps engineering agent.

Your task is to bootstrap a production-grade, enterprise GitOps, DevOps, security, testing, and SRE observability foundation in this repository by extracting best practices from the reference blueprint:
https://github.com/spiralspectra/agentic-gitops-devops-blueprint

### Project Parameters:
- GCP Project ID: [REPLACE_WITH_YOUR_GCP_PROJECT_ID]
- Resource Prefix: [REPLACE_WITH_YOUR_SERVICE_NAME, e.g. customer-service-agent]
- GitHub Repo: [REPLACE_WITH_YOUR_ORG/YOUR_REPO]
- Primary Region: [REPLACE_WITH_REGION, e.g. us-central1]
- Remote State Bucket: [REPLACE_WITH_TF_STATE_BUCKET, e.g. my-project-tfstate]

### Foundational Requirements to Establish:
1. Dual Service Account Workload Identity Federation (WIF):
   - CI Service Account: Read-only on infrastructure, used for pull request checks.
   - Deployer Service Account: Locked to refs/heads/main via GCP IAM condition.
2. 5-Gate Pull Request Workflow (.github/workflows/pr_checks.yaml):
   - Gate 1: Linting & formatting (Ruff + Codespell).
   - Gate 2: Terraform speculative plan guarded against destructive changes (guard_terraform_plan.py).
   - Gate 3: Unit and integration tests (Pytest).
   - Gate 4: Deterministic + LLM-as-a-judge evaluation gate (check_thresholds.py).
   - Gate 5: Frontend container embeddability and health smoke test.
3. Continuous Deployment Workflow (.github/workflows/release.yaml):
   - Serial execution on main (concurrency group cancel-in-progress: false).
   - Terraform apply, agent deployment, and 30-second Locust smoke test.
4. Autonomous Security & CodeMender Loop (codemender/):
   - Offline verification script (codemender/build.sh).
   - Configured for gemini-2.5-pro with --no-model-fallback.
5. 3-Layer Production Observability:
   - Layer 1 Telemetry: GCS logs, Cloud Logging sink, BigQuery completions_view.
   - Layer 2 SRE Monitoring: 28-day availability (99.5%) and latency (p95 <= 8000ms) SLOs, fast-burn and slow-burn alert policies linked to docs/RUNBOOK_ALERTS.md.
   - Layer 3 Evaluation Gate: Quality and safety refusal thresholds.
6. Zero-Trust Data Access (data/views/):
   - 4-Tier SESSION_USER() BigQuery authorized view pattern.

Please inspect the blueprint repository structure, adapt all configuration files with our project parameters, and verify with `codemender/build.sh` before presenting the final result.
```
