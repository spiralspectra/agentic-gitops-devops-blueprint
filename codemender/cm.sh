#!/usr/bin/env bash
# CodeMender wrapper for this repository - use it instead of calling `cm` directly.
#
#   ./codemender/cm.sh health --strict
#   ./codemender/cm.sh find agents --quick
#   ./codemender/cm.sh verify <finding-id>
#   ./codemender/cm.sh fix <finding-id>
#   ./codemender/cm.sh ask "look for prompt injection in tools" agents/
#
# What it does:
#   * runs from the repository root with CM_HOME=codemender/ (committed config.yaml; state stays here),
#   * sets GOOGLE_CLOUD_PROJECT to the target project,
#   * pins the model for find / verify / fix (defaults to gemini-2.5-pro),
#   * passes --no-model-fallback to ensure execution integrity.
#
# Overrides: CM_MODEL (default gemini-2.5-pro), CM_BIN (path to cm), CM_HOME, GOOGLE_CLOUD_PROJECT.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"
export CM_HOME="${CM_HOME:-$REPO_ROOT/codemender}"
MODEL="${CM_MODEL:-gemini-2.5-pro}"
CM_BIN="${CM_BIN:-cm}"

if ! command -v "$CM_BIN" >/dev/null 2>&1; then
  echo "cm not found on PATH - install it as described in codemender/README.md (or set CM_BIN)." >&2
  exit 127
fi

cd "$REPO_ROOT"
args=("$@")

# `ask` - quick scan steered by natural language context
if [ "${1:-}" = "ask" ]; then
  shift
  prompt="${1:-}"
  if [ -z "$prompt" ]; then
    echo "usage: ./codemender/cm.sh ask \"<what to look for>\" [path ...]" >&2
    exit 2
  fi
  shift
  paths=("$@"); [ ${#paths[@]} -eq 0 ] && paths=(.)
  context="$(cat "$REPO_ROOT/codemender/context.txt") Request from the engineer: $prompt"
  args=(find "${paths[@]}" --quick --compact -c "$context")
fi

case "${args[0]:-}" in
  find|verify|fix)
    has_model=false
    for a in "${args[@]}"; do
      case "$a" in --model|--model=*) has_model=true ;; esac
    done
    if [ "$has_model" = false ]; then
      args+=(--model "$MODEL")
    fi
    if [ "${CODEMENDER_ALLOW_FALLBACK:-0}" != "1" ]; then
      args+=(--no-model-fallback)
    fi
    ;;
esac

if [ "${CODEMENDER_DRY_RUN:-0}" = "1" ]; then
  printf 'would run: %q' "$CM_BIN"; printf ' %q' "${args[@]}"; printf '\n'
  exit 0
fi
exec "$CM_BIN" "${args[@]}"
