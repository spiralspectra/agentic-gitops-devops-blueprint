#!/usr/bin/env python3
"""Refuse to auto-apply a Terraform plan that destroys or replaces resources.

The release pipeline applies infrastructure changes on merge to main without a
human at the keyboard. Creating and updating resources is what that is for;
deleting or replacing them (e.g. a renamed bucket, a dataset recreated because a
location changed) must be a conscious decision. Set the repository variable
TF_ALLOW_DESTROY=true for the one run that needs it, then set it back.

Usage: guard_terraform_plan.py <terraform show -json output>
"""

from __future__ import annotations

import json
import os
import sys

DESTRUCTIVE = {"delete"}

# Additive/revocable IAM member bindings that do not destroy stateful data,
# compute, or identity resources. Pipeline bootstrap bindings (`ci*` /
# `deployer*`) remain protected so a plan cannot accidentally lock CI out.
SAFE_IAM_MEMBER_TYPES = {
    "google_bigquery_dataset_iam_member",
    "google_bigquery_table_iam_member",
    "google_project_iam_member",
    "google_storage_bucket_iam_member",
    "google_service_account_iam_member",
    "google_cloud_run_v2_service_iam_member",
    "google_iap_web_backend_service_iam_member",
}
PROTECTED_PIPELINE_BINDING_NAMES = {
    "ci",
    "ci_allowed_objects",
    "ci_tfstate_reader",
    "ci_workload_identity_user",
    "ci_token_creator",
    "deployer",
    "deployer_data_owner",
    "deployer_analytics_owner",
    "deployer_tfstate_admin",
    "deployer_workload_identity_user",
    "deployer_token_creator",
    "telemetry_deployer_owner",
}


def _is_safe_iam_tightening(rc: dict, actions: list[str]) -> bool:
    if not set(actions) <= {"create", "delete"}:
        return False
    res_type = str(rc.get("type") or "")
    res_name = str(rc.get("name") or "")
    if res_type not in SAFE_IAM_MEMBER_TYPES:
        return False
    if res_name in PROTECTED_PIPELINE_BINDING_NAMES:
        return False
    return True


def _is_safe_secret_version_rotation(rc: dict, actions: list[str]) -> bool:
    """Allow zero-downtime create-before-destroy rotation of immutable secret versions."""
    return (
        actions == ["create", "delete"]
        and str(rc.get("type") or "") == "google_secret_manager_secret_version"
    )


def destructive_changes(plan: dict) -> list[tuple[str, list[str]]]:
    found = []
    for rc in plan.get("resource_changes") or []:
        actions = (rc.get("change") or {}).get("actions") or []
        if DESTRUCTIVE & set(actions):
            if _is_safe_iam_tightening(rc, actions) or _is_safe_secret_version_rotation(
                rc, actions
            ):
                continue
            found.append((rc.get("address", "?"), actions))
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        plan = json.load(f)

    found = destructive_changes(plan)
    if not found:
        print("Plan contains no destroy/replace actions.")
        return 0

    allow = os.environ.get("TF_ALLOW_DESTROY", "").strip().lower() == "true"
    print(f"Plan contains {len(found)} destructive action(s):")
    for address, actions in found:
        print(f"  {address}: {' -> '.join(actions)}")
    if allow:
        print("TF_ALLOW_DESTROY=true: proceeding.")
        return 0
    print(
        "\nRefusing to apply automatically. If this is intended, set the GitHub "
        "repository variable TF_ALLOW_DESTROY=true and re-run the release, "
        "then set it back to false.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
