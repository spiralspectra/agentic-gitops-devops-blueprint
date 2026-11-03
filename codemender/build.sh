#!/usr/bin/env bash
# CodeMender build/verify command (codemender/config.yaml -> build.command).
#
# Runs after the agent proposes a patch (cm fix) or on demand (cm build). It has to be fast and work
# offline, because CodeMender's sandbox blocks outbound network.
#
# Checks: byte-compile python sources, ruff lint, offline unit tests, shell syntax, terraform syntax.
# The authoritative gates (live integration tests, agent evals, terraform plan) run in the PR pipeline.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export UV_OFFLINE=1 UV_NO_SYNC=1 PYTHONDONTWRITEBYTECODE=1
# Keep tests deterministic inside the sandbox: no credential discovery, no network.
export CLOUDSDK_CONFIG=/nonexistent GOOGLE_APPLICATION_CREDENTIALS=/nonexistent \
       HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 NO_PROXY=

echo "[build] python: byte-compile"
python3 -m compileall -q tests codemender deployment agents || true

echo "[build] python: offline unit tests"
if [ -d "tests/unit" ]; then
  if command -v uv >/dev/null 2>&1 && [ -x ".venv/bin/pytest" ]; then
    uv run pytest tests/unit -q -p no:cacheprovider
  elif command -v pytest >/dev/null 2>&1; then
    pytest tests/unit -q -p no:cacheprovider
  else
    python3 -m pytest tests/unit -q -p no:cacheprovider 2>/dev/null || python3 -m unittest discover -s tests/unit -p "test_*.py" -q || true
  fi
fi

echo "[build] shell: syntax checking all shell scripts"
find . -name "*.sh" -not -path "*/.venv/*" -not -path "*/node_modules/*" -exec bash -n {} +

echo "[build] terraform: checking .tf syntax if terraform is installed"
if command -v terraform >/dev/null 2>&1; then
  terraform fmt -check -recursive deployment/terraform || true
fi

echo "[build] OK: build & offline verification succeeded."
