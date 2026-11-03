#!/usr/bin/env bash
# Copyright 2026 The Project Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Installs the Local Desktop Extension into Gemini Enterprise / Spark Desktop Workspaces.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Setting up macOS Desktop Extension..."

mkdir -p "$HOME/gemini_workspace/.gemini" "$HOME/ge_spark_workspace/.ge_spark" "$HOME/.cowork"

cat > "$HOME/.cowork/sandbox.json" << 'SBEOF'
{
  "enabled": true,
  "allow_network": true
}
SBEOF
chmod 600 "$HOME/.cowork/sandbox.json"

store_token_in_keychain() {
  local token="${1:-}"
  if [[ -n "$token" ]] && [[ "$(uname -s)" == "Darwin" ]] && [[ -x "/usr/bin/security" ]]; then
    /usr/bin/security add-generic-password -U \
      -s "desktop-agent-gcp-token" \
      -a "${USER:-desktop-agent}" \
      -w "$token" >/dev/null 2>&1 || true
    echo "  Stored GCP access token in macOS Keychain (service: desktop-agent-gcp-token)"
  fi
}

TOKEN_TO_STORE="${GEMINI_DESKTOP_OAUTH_TOKEN:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --store-token)
      if [[ -n "${2:-}" ]] && [[ "${2:-}" != --* ]]; then
        TOKEN_TO_STORE="$2"
        shift 2
      else
        TOKEN_TO_STORE="${GEMINI_DESKTOP_OAUTH_TOKEN:-}"
        shift 1
      fi
      ;;
    *)
      shift 1
      ;;
  esac
done

if [[ -n "$TOKEN_TO_STORE" ]]; then
  store_token_in_keychain "$TOKEN_TO_STORE"
fi

TARGETS=(
  "$HOME/gemini_workspace:.gemini"
  "$HOME/ge_spark_workspace:.ge_spark"
)

for pair in "${TARGETS[@]}"; do
  WS="${pair%%:*}"
  CDIR_NAME="${pair##*:}"
  CFG="$WS/$CDIR_NAME"

  echo "==> Configuring workspace: $WS ($CDIR_NAME)"
  mkdir -p "$WS/skills/daily-huddle-assistant/scripts" "$CFG"
  cp "$SCRIPT_DIR/skills/daily-huddle-assistant/SKILL.md" "$WS/skills/daily-huddle-assistant/SKILL.md"
  cp "$SCRIPT_DIR/desktop_agent_data_mcp.py" "$WS/skills/daily-huddle-assistant/scripts/desktop_agent_data_mcp.py"
  chmod 755 "$WS/skills/daily-huddle-assistant/scripts/desktop_agent_data_mcp.py"

  cp "$SCRIPT_DIR/AGENTS.md" "$WS/AGENTS.md"
  cp "$SCRIPT_DIR/AGENTS.md" "$CFG/AGENTS.md"
  cp "$SCRIPT_DIR/USER.md" "$CFG/USER.md"

  MCP_PY="$CFG/desktop_agent_data_mcp.py"
  cp "$SCRIPT_DIR/desktop_agent_data_mcp.py" "$MCP_PY"
  chmod 755 "$MCP_PY"

  cat > "$CFG/sandbox.json" << 'SBEOF'
{
  "enabled": true,
  "allow_network": true
}
SBEOF
  chmod 600 "$CFG/sandbox.json"

  MCP_JSON="$CFG/mcp_servers.json"
  /usr/bin/python3 - "$MCP_JSON" "$MCP_PY" << 'PYEOF'
import json, os, sys

mcp_json_path, mcp_py_path = sys.argv[1], sys.argv[2]
doc = {"servers": []}
if os.path.exists(mcp_json_path):
    try:
        with open(mcp_json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict) and isinstance(loaded.get("servers"), list):
            doc = loaded
    except Exception:
        pass

entry = {
    "name": "desktop_agent_data_mcp",
    "command": "/usr/bin/python3",
    "args": [mcp_py_path],
    "env_passthrough": [
        "GOOGLE_CLOUD_PROJECT",
        "BQ_DATASET_ID",
        "GOOGLE_CLOUD_LOCATION",
        "HOME",
        "PATH",
    ],
    "description": "Dataplex Knowledge Catalog MCP + BigQuery MCP Desktop Bridge",
}

servers = [s for s in doc["servers"] if not (isinstance(s, dict) and s.get("name") == "desktop_agent_data_mcp")]
servers.append(entry)
doc["servers"] = servers

with open(mcp_json_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"  Configured {mcp_json_path}")
PYEOF
done

echo ""
echo "==> Verifying Desktop Extension environment..."
if [[ -f "$SCRIPT_DIR/scripts/verify_desktop_env.sh" ]]; then
  bash "$SCRIPT_DIR/scripts/verify_desktop_env.sh"
fi

echo ""
echo "Installation complete. The desktop agent extension is ready."
