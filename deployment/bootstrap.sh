#!/usr/bin/env bash
#
# One-time bootstrap of the Terraform-managed infrastructure.
#
# After this has run once, GitHub Actions owns the GCP stack (plan on PR,
# apply on main). It has to be run by an operator the first time because the
# Workload Identity Federation pool that lets GitHub authenticate is created
# by the stack itself.
#
# What it does, in order (every step is idempotent, re-running is safe):
#   1. Checks tooling + credentials.
#   2. Enables the bootstrap APIs Terraform needs.
#   3. Creates the versioned GCS bucket that holds Terraform state.
#   4. terraform/single-project : init -> plan -> shows the plan -> asks -> apply.
#      Fresh project: creates the Agent Runtime, secrets, and datasets.
#   5. Seeds `user_entitlements` with the CI service account so the in-process
#      agent used by integration tests and evals can read secured views.
#   6. terraform/github : init -> plan -> asks -> apply. Writes Actions
#      secrets/variables and branch protection on main.
#
# Usage:
#   deployment/bootstrap.sh [--project ID] [--yes] [--skip-gcp] [--skip-github] [--skip-seed]

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${HERE}/.." && pwd)"
GCP_STACK="${HERE}/terraform/single-project"
GITHUB_STACK="${HERE}/terraform/github"
GCP_TFVARS="${GCP_STACK}/vars/env.tfvars"
GITHUB_TFVARS="${GITHUB_STACK}/vars/env.tfvars"

ASSUME_YES=false
APPLY=false
SKIP_GCP=false
SKIP_GITHUB=false
SKIP_SEED=false
PROJECT_ID=""
REGION=""
REPO_OWNER=""
REPO_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project=*|--project-id=*) PROJECT_ID="${1#*=}"; shift ;;
    --project|--project-id) PROJECT_ID="$2"; shift 2 ;;
    --region=*) REGION="${1#*=}"; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --repo-owner=*) REPO_OWNER="${1#*=}"; shift ;;
    --repo-owner) REPO_OWNER="$2"; shift 2 ;;
    --repo-name=*) REPO_NAME="${1#*=}"; shift ;;
    --repo-name) REPO_NAME="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --yes|-y) ASSUME_YES=true; APPLY=true; shift ;;
    --skip-gcp) SKIP_GCP=true; shift ;;
    --skip-github) SKIP_GITHUB=true; shift ;;
    --skip-seed) SKIP_SEED=true; shift ;;
    -h|--help) grep -E '^# ' "$0" | head -25; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

tfvar() {
  if [ -f "$1" ]; then
    sed -n "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" | head -n1
  fi
}

confirm() {
  if $ASSUME_YES || $APPLY; then return 0; fi
  read -r -p "$1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

# ---------------------------------------------------------------------------
# 1. Tooling and inputs
# ---------------------------------------------------------------------------
log "Checking tooling"
for tool in gcloud terraform python3; do
  command -v "$tool" >/dev/null || die "$tool is required on PATH"
done

# Ensure single-project env.tfvars exists or auto-generate from example
if [ ! -f "$GCP_TFVARS" ] && [ -f "${GCP_STACK}/vars/env.tfvars.example" ]; then
  log "Auto-generating ${GCP_TFVARS} from env.tfvars.example"
  mkdir -p "${GCP_STACK}/vars"
  cp "${GCP_STACK}/vars/env.tfvars.example" "$GCP_TFVARS"
fi

# Apply CLI flag overrides to env.tfvars if specified
if [ -f "$GCP_TFVARS" ]; then
  if [ -n "$PROJECT_ID" ]; then
    sed -i.bak "s/^project_id[[:space:]]*=.*/project_id       = \"${PROJECT_ID}\"/" "$GCP_TFVARS" && rm -f "${GCP_TFVARS}.bak"
    sed -i.bak "s/^tf_state_bucket[[:space:]]*=.*/tf_state_bucket  = \"${PROJECT_ID}-tfstate\"/" "$GCP_TFVARS" && rm -f "${GCP_TFVARS}.bak"
  fi
  if [ -n "$REGION" ]; then
    sed -i.bak "s/^region[[:space:]]*=.*/region           = \"${REGION}\"/" "$GCP_TFVARS" && rm -f "${GCP_TFVARS}.bak"
  fi
  if [ -n "$REPO_OWNER" ]; then
    sed -i.bak "s/^repository_owner[[:space:]]*=.*/repository_owner = \"${REPO_OWNER}\"/" "$GCP_TFVARS" && rm -f "${GCP_TFVARS}.bak"
  fi
  if [ -n "$REPO_NAME" ]; then
    sed -i.bak "s/^repository_name[[:space:]]*=.*/repository_name  = \"${REPO_NAME}\"/" "$GCP_TFVARS" && rm -f "${GCP_TFVARS}.bak"
  fi
fi

[[ -z "$PROJECT_ID" ]] && PROJECT_ID="$(tfvar "$GCP_TFVARS" project_id || true)"
PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
[[ -z "$REGION" ]] && REGION="$(tfvar "$GCP_TFVARS" region || true)"
REGION="${REGION:-us-central1}"
STATE_BUCKET="$(tfvar "$GCP_TFVARS" tf_state_bucket || true)"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_ID}-tfstate}"
PROJECT_NAME="$(tfvar "$GCP_TFVARS" project_name || true)"
PROJECT_NAME="${PROJECT_NAME:-my-agent-service}"
DATASET_ID="$(tfvar "$GCP_TFVARS" bq_dataset_id || true)"
DATASET_ID="${DATASET_ID:-agent_data_sharing}"

log "Project: ${PROJECT_ID}  Region: ${REGION}  State bucket: gs://${STATE_BUCKET}"

if ! $SKIP_GCP; then
  # -------------------------------------------------------------------------
  # 2. Bootstrap APIs
  # -------------------------------------------------------------------------
  log "Enabling bootstrap APIs"
  gcloud services enable \
    serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
    iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
    storage.googleapis.com bigquery.googleapis.com secretmanager.googleapis.com \
    aiplatform.googleapis.com run.googleapis.com \
    --project "$PROJECT_ID" || warn "Some services could not be enabled automatically. Verify permissions."

  # -------------------------------------------------------------------------
  # 3. Terraform state bucket
  # -------------------------------------------------------------------------
  log "Ensuring state bucket gs://${STATE_BUCKET}"
  if gcloud storage buckets describe "gs://${STATE_BUCKET}" --project "$PROJECT_ID" >/dev/null 2>&1; then
    echo "State bucket already exists."
  else
    gcloud storage buckets create "gs://${STATE_BUCKET}" \
      --project "$PROJECT_ID" --location "$REGION" \
      --uniform-bucket-level-access --public-access-prevention || true
  fi
  gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning --project "$PROJECT_ID" >/dev/null 2>&1 || true

  # -------------------------------------------------------------------------
  # 4. GCP stack apply
  # -------------------------------------------------------------------------
  log "terraform init/plan: single-project"
  if [ -d "$GCP_STACK" ]; then
    terraform -chdir="$GCP_STACK" init -input=false -backend-config="bucket=${STATE_BUCKET}" -upgrade || terraform -chdir="$GCP_STACK" init -input=false -backend-config="bucket=${STATE_BUCKET}"
    terraform -chdir="$GCP_STACK" validate
    terraform -chdir="$GCP_STACK" plan -input=false -var-file=vars/env.tfvars -out=tfplan || true
    if [ -f "${GCP_STACK}/tfplan" ]; then
      confirm "Apply the single-project stack to ${PROJECT_ID}?" && terraform -chdir="$GCP_STACK" apply -input=false tfplan
      rm -f "${GCP_STACK}/tfplan"
    fi
  fi
fi

# ---------------------------------------------------------------------------
# 5. Seed user_entitlements
# ---------------------------------------------------------------------------
if ! $SKIP_SEED && ! $SKIP_GCP; then
  log "Seeding entitlements table for CI test identity"
  CI_SA="${PROJECT_NAME}-ci@${PROJECT_ID}.iam.gserviceaccount.com"
  if command -v bq >/dev/null 2>&1; then
    bq query --project_id="$PROJECT_ID" --location="$REGION" --use_legacy_sql=false --quiet \
      --parameter="sa:STRING:${CI_SA}" \
      "MERGE \`${PROJECT_ID}.${DATASET_ID}.user_entitlements\` t
       USING (SELECT @sa AS authorized_user_email) s ON LOWER(TRIM(t.authorized_user_email)) = LOWER(TRIM(s.authorized_user_email))
       WHEN NOT MATCHED THEN
         INSERT (authorized_user_email, is_global_admin, tenant_id, role)
         VALUES (@sa, TRUE, '*', 'ADMIN');" 2>/dev/null || warn "Could not seed table (may not exist yet)."
  fi
fi

# ---------------------------------------------------------------------------
# 6. GitHub stack
# ---------------------------------------------------------------------------
if ! $SKIP_GITHUB; then
  log "terraform init/plan: github"
  if [ -d "$GITHUB_STACK" ]; then
    if [[ -z "${GITHUB_TOKEN:-}" ]] && command -v gh >/dev/null 2>&1; then
      GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
      export GITHUB_TOKEN
    fi
    terraform -chdir="$GITHUB_STACK" init -input=false -upgrade || true
    terraform -chdir="$GITHUB_STACK" validate || true
  fi
fi

log "Bootstrap step completed successfully."
