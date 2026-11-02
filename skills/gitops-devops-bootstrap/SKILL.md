---
name: gitops-devops-bootstrap
description: Instructs an AI coding agent on how to bootstrap a production-grade GitOps, DevOps, Terraform WIF, CI/CD 5-gate PR pipeline, CodeMender verification loop, and 3-layer SRE observability foundation for AI agent applications on Google Cloud before writing application code.
---

# GitOps & DevOps Bootstrap Skill

Use this skill when scaffolding or bootstrapping any new enterprise AI agent or cloud application repository on Google Cloud and GitHub.

## Core Mandate
Always establish the foundational security, testing, and continuous delivery gates **before** writing feature code:
1. Workload Identity Federation (WIF) with Dual Service Account isolation.
2. 5-Gate Pull Request verification pipeline (`lint`, `terraform-plan`, `tests`, `evals`, `frontend-build`).
3. Serial release pipeline on `main`.
4. CodeMender sandboxed verification loop.
5. 3-Layer production observability (Telemetry, SRE SLOs + Alerts, Eval Gates).
6. Zero-trust data access via `SESSION_USER()` BigQuery authorized views.

---

## Parameterization Table

When applying this blueprint to a new project, substitute placeholders as follows:

| Placeholder | Example Replacement | Description |
| :--- | :--- | :--- |
| `your-gcp-project-id` | `acme-agent-prod-1234` | Target Google Cloud Project ID |
| `my-agent-service` | `customer-support-agent` | Base kebab-case resource naming prefix |
| `your-org` | `my-enterprise-org` | GitHub organization or username |
| `your-repo` | `support-agent-service` | GitHub repository name |
| `us-central1` | `europe-west2` | Primary Google Cloud deployment region |
| `your-gcp-project-id-tfstate` | `acme-agent-tfstate` | Cloud Storage bucket for Terraform remote state |

---

## Step-by-Step Bootstrap Checklist

### Step 1: Copy Blueprint Scaffolding
Copy the core directory layout into the target repository root:
- `.github/workflows/` (`pr_checks.yaml`, `release.yaml`, `project_board_sync.yaml`)
- `.github/pull_request_template.md` and `.github/dependabot.yml`
- `deployment/` (`bootstrap.sh`, `ci/`, `terraform/`)
- `codemender/` (`build.sh`, `cm.sh`, `config.yaml`, `context.txt`)
- `tests/` (`ci/`, `eval/`, `load_test/`, `unit/`, `integration/`)
- `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`
- `docs/RUNBOOK_ALERTS.md`

### Step 2: Bootstrap Cloud Infrastructure
1. Authenticate with Google Cloud:
   ```bash
   gcloud auth application-default login
   gcloud config set project your-gcp-project-id
   ```
2. Execute the bootstrap script:
   ```bash
   ./deployment/bootstrap.sh \
     --project-id="your-gcp-project-id" \
     --repo-owner="your-org" \
     --repo-name="your-repo"
   ```

### Step 3: Wire GitHub Secrets & Branch Protection
1. Apply the GitHub Terraform stack:
   ```bash
   cd deployment/terraform/github
   terraform init -backend-config="bucket=your-gcp-project-id-tfstate"
   terraform apply -var-file=vars/env.tfvars
   ```
2. Confirm branch protection requires all 5 status checks:
   - `lint`
   - `terraform-plan`
   - `tests`
   - `evals`
   - `frontend-build`

### Step 4: Verify Local Verification Loop
Run the CodeMender and test verification loop locally:
```bash
bash ./codemender/build.sh
uv run pytest tests/unit tests/integration -v
uv run python tests/eval/check_thresholds.py
```
