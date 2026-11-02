#!/usr/bin/env python3
"""Check that every pointer to the Agent Runtime agrees.

Multiple places name the engine and they must all refer to the same one, or
`agents-cli deploy` silently creates a second engine that Terraform, IAM and
the platform know nothing about:

  * deployment/terraform/single-project/vars/env.tfvars  -> reasoning_engine_id
  * agents/starter_agent/deployment_metadata.json        -> remote_agent_runtime_id
  * Terraform state (optional, --state-engine)           -> reasoning_engine_name

Only the trailing numeric ID is compared: the API reports the project by
number, the tfvars by ID.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


def engine_id_from_tfvars(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\s*reasoning_engine_id\s*=\s*"([^"]*)"', line)
            if m:
                val = m.group(1).strip()
                return val
    return ""


def engine_id_from_metadata(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    engine = (meta.get("remote_agent_runtime_id") or meta.get("reasoning_engine_id") or "").rstrip(
        "/"
    )
    if not engine:
        return ""
    return engine.split("/")[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tfvars", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument(
        "--state-engine",
        default="",
        help="terraform output reasoning_engine_name (may be empty before bootstrap)",
    )
    parser.add_argument(
        "--require-state",
        action="store_true",
        help="require state engine to be non-empty and matching (if state is initialized)",
    )
    args = parser.parse_args(argv)

    tfvars_id = engine_id_from_tfvars(args.tfvars)
    metadata_id = engine_id_from_metadata(args.metadata)
    state_id = args.state_engine.rstrip("/").split("/")[-1] if args.state_engine.strip() else ""

    print(f"tfvars   reasoning_engine_id    : {tfvars_id or '(not set)'}")
    print(f"metadata remote_agent_runtime_id: {metadata_id or '(not set)'}")
    print(f"state    reasoning_engine_name  : {state_id or '(not available)'}")

    # If neither is set yet (bootstrap phase) and state is not required, pass cleanly
    if not tfvars_id and not metadata_id and not state_id and not args.require_state:
        print("INFO: Engine IDs not yet configured. Skipping check during initial setup.")
        return 0

    problems = []
    if args.require_state and not state_id:
        problems.append("--require-state requested but --state-engine is empty or not provided")

    if tfvars_id and metadata_id and tfvars_id != metadata_id:
        problems.append(
            f"deployment_metadata.json ({metadata_id}) and env.tfvars ({tfvars_id}) name different engines"
        )
    if state_id and tfvars_id and state_id != tfvars_id:
        problems.append(
            f"Terraform state ({state_id}) names a different engine than env.tfvars ({tfvars_id})"
        )

    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        print(
            "Fix: The service must point to exactly one Agent Runtime. Align deployment_metadata.json "
            "and env.tfvars before releasing.",
            file=sys.stderr,
        )
        return 1
    print("OK: all engine pointers agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
