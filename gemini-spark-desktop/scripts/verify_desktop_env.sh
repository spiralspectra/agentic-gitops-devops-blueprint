#!/usr/bin/env bash
# Copyright 2026 The Project Contributors
# Licensed under the Apache License, Version 2.0
set -euo pipefail

echo "==> Verifying macOS Desktop Extension Environment..."

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "INFO: Non-macOS environment detected. Skipping Darwin-specific verification."
  exit 0
fi

echo "--> Checking sandbox-exec utility..."
which sandbox-exec > /dev/null && echo "PASS: sandbox-exec located."

echo "--> Checking Seatbelt sandbox profile..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sandbox-exec -f "${SCRIPT_DIR}/sandbox.sb" /bin/echo "PASS: Sandbox profile initialized successfully."

echo "--> Checking System Keychain access..."
which security > /dev/null && echo "PASS: security CLI available."

echo "==> Desktop Extension Environment is Healthy."
