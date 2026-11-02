# Terraform GitOps Infrastructure Stacks

This directory contains the Terraform stacks that manage Google Cloud infrastructure and GitHub repository settings for the agent service.

## Architecture

```
deployment/terraform/
├── single-project/      # Google Cloud infrastructure (APIs, WIF, SAs, BQ, Storage, Secrets)
└── github/              # GitHub repository configuration (Secrets, Vars, Environments, Branch Protection)
```

### 1. `single-project` Stack
Provisions all Google Cloud resources required to run and test the agent:
- **Workload Identity Federation (WIF)**: Allows GitHub Actions to authenticate without static service account keys.
- **Dual Service Accounts**:
  - `ci`: Read-only identity used by pull request workflows (`roles/viewer`, `roles/iam.securityReviewer`, `roles/bigquery.jobUser`).
  - `deployer`: Deploy identity locked to `refs/heads/main` (`roles/aiplatform.admin`, `roles/run.admin`, `roles/storage.admin`, etc.).
- **BigQuery Dataset**: Hosts agent evaluation metrics and telemetry logs.
- **Cloud Storage Bucket**: Manages deployment artifacts and staging files.
- **Secret Manager**: Securely stores API keys and credentials.

### 2. `github` Stack
Wires Google Cloud outputs directly into GitHub Actions:
- Provisions Actions and Dependabot secrets (`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_CI_SERVICE_ACCOUNT`, `GCP_DEPLOYER_SERVICE_ACCOUNT`).
- Configures repository variables (`GCP_PROJECT_ID`, `GCP_REGION`, `TF_STATE_BUCKET`).
- Enforces branch protection on `main` requiring the 5 status checks:
  1. `lint`
  2. `terraform-plan`
  3. `tests`
  4. `evals`
  5. `frontend-build`

## Getting Started

Run the bootstrap script to provision state storage and run initial configuration:
```bash
./deployment/bootstrap.sh \
  --project-id="your-gcp-project-id" \
  --repo-owner="your-org" \
  --repo-name="your-repo"
```
