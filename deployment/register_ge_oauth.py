#!/usr/bin/env python3
"""Idempotently creates/updates the Gemini Enterprise OAuth 2.0 Authorization and attaches it live.

Registers a Discovery Engine `Authorization` (`serverSideOauth2`) requesting the
`https://www.googleapis.com/auth/bigquery` scope so the platform injects the
signed-in user's Google OAuth access token into tool context. That makes BigQuery
`SESSION_USER()` evaluate to the signed-in user instead of the shared service identity.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.parse

import google.auth
import requests
from google.auth.transport.requests import Request

REDIRECT_URI = "https://vertexaisearch.cloud.google.com/static/oauth/oauth.html"
DEFAULT_SCOPES = "https://www.googleapis.com/auth/bigquery"
DEFAULT_GITHUB_REPO = "your-org/your-repo"
METADATA_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "agents"
    / "starter_agent"
    / "deployment_metadata.json"
)


def _build_authorization_uri(client_id: str, scopes: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
        "include_granted_scopes": "true",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def _get_access_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError(
            "Could not obtain a GCP access token from Application Default Credentials."
        )
    return creds.token


def _resolve_project_number(project: str, token: str) -> str:
    if project.isdigit():
        return project
    resp = requests.get(
        f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    number = str(resp.json().get("projectNumber") or "").strip()
    if not number:
        raise RuntimeError(f"Could not resolve projectNumber for {project!r}.")
    return number


def _endpoint_prefix(location: str) -> str:
    if location == "global":
        return "https://discoveryengine.googleapis.com"
    return f"https://{location}-discoveryengine.googleapis.com"


def _default_reasoning_engine() -> str:
    if METADATA_PATH.exists():
        try:
            meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            val = str(meta.get("remote_agent_runtime_id") or "").strip()
            if val:
                return val
        except Exception:
            pass
    return ""


def upsert_authorization(
    *,
    project: str,
    location: str,
    auth_id: str,
    client_id: str,
    client_secret: str,
    scopes: str = DEFAULT_SCOPES,
    dry_run: bool = False,
) -> str:
    auth_uri = _build_authorization_uri(client_id, scopes)
    if dry_run:
        proj_display = project if project.isdigit() else f"<number-for:{project}>"
        resource_name = f"projects/{proj_display}/locations/{location}/authorizations/{auth_id}"
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "resource_name": resource_name,
                    "redirect_uri_required": REDIRECT_URI,
                    "scopes": scopes,
                    "authorization_uri": auth_uri,
                },
                indent=2,
            )
        )
        return resource_name

    token = _get_access_token()
    project_number = _resolve_project_number(project, token)
    resource_name = f"projects/{project_number}/locations/{location}/authorizations/{auth_id}"
    base = _endpoint_prefix(location)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_number,
    }
    body = {
        "name": resource_name,
        "serverSideOauth2": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "authorizationUri": auth_uri,
            "tokenUri": "https://oauth2.googleapis.com/token",
        },
    }

    get_resp = requests.get(f"{base}/v1alpha/{resource_name}", headers=headers, timeout=20)
    if get_resp.status_code == 404:
        create_url = (
            f"{base}/v1alpha/projects/{project_number}/locations/{location}/authorizations"
            f"?authorizationId={urllib.parse.quote(auth_id)}"
        )
        resp = requests.post(create_url, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        action = "created"
    else:
        get_resp.raise_for_status()
        patch_url = f"{base}/v1alpha/{resource_name}?updateMask=serverSideOauth2"
        resp = requests.patch(patch_url, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        action = "updated"

    print(f"{action} Discovery Engine Authorization: {resource_name}")
    print(f"Set GEMINI_AUTHORIZATION_ID={resource_name}")
    return resource_name


def patch_ge_adk_agent(
    *,
    gemini_app_id: str,
    reasoning_engine: str,
    authorization_resource: str = "",
    ensure_all_users_sharing: bool = True,
    token: str | None = None,
) -> str:
    """Attaches toolAuthorizations and/or ALL_USERS sharingConfig onto the live agent."""
    tok = token or _get_access_token()
    parts = gemini_app_id.strip("/").split("/")
    if len(parts) < 8 or parts[0] != "projects" or parts[2] != "locations":
        raise ValueError(f"Invalid --gemini-app-id: {gemini_app_id!r}")
    project_number = parts[1]
    app_location = parts[3]
    base = _endpoint_prefix(app_location)
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_number,
    }
    list_url = f"{base}/v1alpha/{gemini_app_id.strip('/')}/assistants/default_assistant/agents"
    resp = requests.get(list_url, headers=headers, timeout=20)
    resp.raise_for_status()
    agents = resp.json().get("agents") or []

    target_tail = reasoning_engine.strip().rsplit("/", 1)[-1]
    matched_name = ""
    for ag in agents:
        re_name = (
            (ag.get("adkAgentDefinition") or {}).get("provisionedReasoningEngine") or {}
        ).get("reasoningEngine", "")
        if re_name == reasoning_engine or (target_tail and re_name.endswith(f"/{target_tail}")):
            matched_name = str(ag.get("name") or "")
            break

    if not matched_name:
        raise RuntimeError(
            f"No agent registered on {gemini_app_id} for Reasoning Engine {reasoning_engine}."
        )

    mask_fields: list[str] = []
    patch_body: dict = {}
    if authorization_resource:
        mask_fields.append("authorizationConfig")
        patch_body["authorizationConfig"] = {"toolAuthorizations": [authorization_resource]}
    if ensure_all_users_sharing:
        mask_fields.append("sharingConfig")
        patch_body["sharingConfig"] = {"scope": "ALL_USERS"}

    if not mask_fields:
        return matched_name

    patch_url = f"{base}/v1alpha/{matched_name}?updateMask={','.join(mask_fields)}"
    patch_resp = requests.patch(patch_url, headers=headers, json=patch_body, timeout=20)
    patch_resp.raise_for_status()
    print(f"patched agent {matched_name} ({','.join(mask_fields)})")
    return matched_name


def persist_github_actions_variable(*, github_repo: str, resource_name: str) -> bool:
    gh_bin = shutil.which("gh")
    if not gh_bin or not github_repo:
        print(
            f"Run manually to persist for CI releases:\n  gh variable set GEMINI_AUTHORIZATION_ID --repo {github_repo or DEFAULT_GITHUB_REPO} --body {resource_name!r}"
        )
        return False
    proc = subprocess.run(
        [
            gh_bin,
            "variable",
            "set",
            "GEMINI_AUTHORIZATION_ID",
            "--repo",
            github_repo,
            "--body",
            resource_name,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        print(f"updated GitHub Actions variable GEMINI_AUTHORIZATION_ID on {github_repo}")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id"),
        help="GCP project ID or project number.",
    )
    parser.add_argument(
        "--location",
        default=os.getenv("GEMINI_ENTERPRISE_LOCATION", "global"),
        help="Discovery Engine location (global, eu, us).",
    )
    parser.add_argument(
        "--auth-id",
        default=os.getenv("APP_AUTH_ID", "app-bigquery-oauth"),
        help="Short authorization ID.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("OAUTH_CLIENT_ID", ""),
        help="OAuth 2.0 Web Client ID.",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("OAUTH_CLIENT_SECRET", ""),
        help="OAuth 2.0 Web Client Secret.",
    )
    parser.add_argument(
        "--scopes",
        default=DEFAULT_SCOPES,
        help="Space-delimited OAuth scopes.",
    )
    parser.add_argument(
        "--gemini-app-id",
        default=os.getenv("GEMINI_APP_ID") or os.getenv("GEMINI_ENTERPRISE_APP_ID") or "",
        help="Full Discovery Engine app/engine resource name.",
    )
    parser.add_argument(
        "--reasoning-engine-id",
        default=os.getenv("AGENT_RUNTIME_ID") or _default_reasoning_engine(),
        help="Reasoning Engine resource name or ID.",
    )
    parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help="GitHub owner/repo where GEMINI_AUTHORIZATION_ID Actions variable is stored.",
    )
    parser.add_argument(
        "--ensure-agent-sharing",
        action="store_true",
        help="Post-publish helper: ensure sharingConfig=ALL_USERS.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print payload without calling GCP.",
    )
    args = parser.parse_args(argv)

    if args.ensure_agent_sharing:
        if not args.gemini_app_id or not args.reasoning_engine_id:
            print(
                "INFO: --ensure-agent-sharing requested but gemini_app_id or reasoning_engine_id not set. Skipping."
            )
            return 0
        auth_res = os.getenv("GEMINI_AUTHORIZATION_ID", "").strip()
        patch_ge_adk_agent(
            gemini_app_id=args.gemini_app_id.strip(),
            reasoning_engine=args.reasoning_engine_id.strip(),
            authorization_resource=auth_res,
            ensure_all_users_sharing=True,
        )
        return 0

    if not args.client_id.strip() or (not args.dry_run and not args.client_secret.strip()):
        print(
            "ERROR: --client-id and --client-secret are required (or run with --dry-run).",
            file=sys.stderr,
        )
        return 2

    resource_name = upsert_authorization(
        project=args.project.strip(),
        location=args.location.strip(),
        auth_id=args.auth_id.strip().rsplit("/", 1)[-1],
        client_id=args.client_id.strip(),
        client_secret=args.client_secret.strip(),
        scopes=args.scopes.strip(),
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        if args.gemini_app_id.strip() and args.reasoning_engine_id.strip():
            patch_ge_adk_agent(
                gemini_app_id=args.gemini_app_id.strip(),
                reasoning_engine=args.reasoning_engine_id.strip(),
                authorization_resource=resource_name,
                ensure_all_users_sharing=True,
            )
        persist_github_actions_variable(
            github_repo=args.github_repo.strip(),
            resource_name=resource_name,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
