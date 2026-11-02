# Operational Law for AI Agents & Developers

This repository is governed by the following strict architectural, operational, and security rules. All AI coding agents, automation workflows, and contributors MUST comply with these instructions.

---

## 1. Zero-Trust Security & Identity

- **No Secrets**: Never commit API keys, service account JSON keys, OAuth credentials, or authentication tokens. All cloud authentication must flow through Workload Identity Federation (WIF) or Secret Manager.
- **Dual Service Account Discipline**:
  - CI operations must exclusively use the read-only CI service account.
  - Deployer permissions are restricted strictly to runs on `refs/heads/main`.
- **Row-Level Security**:
  - All direct data access must go through authorized views enforcing `LOWER(TRIM(SESSION_USER()))` and `WHERE EXISTS` security predicates.
  - Base raw tables must never be exposed directly to end-user queries.

---

## 2. Model Usage & Reference Constraints

- **Allowed Models**:
  - Complex reasoning, tool orchestration, and automated code repair: `gemini-2.5-pro`.
  - High-throughput inference, evaluation judges, and lightweight tasks: `gemini-2.5-flash`.
- **Prohibited Identifiers**:
  - Never reference pre-release, unreleased, or internal model codenames.
  - Only standard, publicly documented Gemini model identifiers may be used.

---

## 3. Hygiene & Sanitization Constraints

- **No Proprietary Customer References**:
  - Never introduce customer-specific names, account identifiers, project names, or private business context into code, comments, documentation, or commit messages.
- **No Internal References**:
  - Strip all internal links, bug references, change list numbers, corp hostnames, and internal LDAPs.
- **Commit Attribution**:
  - Never add `Co-Authored-By` trailers to commits.
  - Commit author email must match your verified organizational or GitHub identity (`git config --global user.useConfigOnly true`), with zero `Co-Authored-By` bot trailers.

---

## 4. CI/CD & Infrastructure Discipline

- **The Five Verification Gates**:
  - Every PR must pass all five required status checks: `lint`, `terraform-plan`, `tests`, `evals`, and `frontend-build`.
  - Never weaken, skip, or delete a test or eval threshold to turn a build green.
- **Terraform Plan Guards**:
  - Destructive actions (`delete` on stateful resources) are prohibited in automated CI runs.
  - Stateful resources (GCS buckets, BigQuery datasets, Reasoning Engine instances) must declare `prevent_destroy = true`.
- **Engine Triple-Pointer Consistency**:
  - Any change to the Reasoning Engine ID must remain synchronized across `env.tfvars`, `deployment_metadata.json`, and Terraform state.

---

## 5. Verification Before Done

Before concluding any implementation task:
1. Run code formatting and linting: `uv run ruff format --check .` and `uv run ruff check .`
2. Run spell checks: `uv run codespell .`
3. Run the unit and integration test suite: `AGENT_EVAL_MOCK=1 uv run pytest tests/unit tests/integration`
4. Run the CodeMender build check: `bash ./codemender/build.sh`
5. Verify exit status is 0 across all verification steps.
