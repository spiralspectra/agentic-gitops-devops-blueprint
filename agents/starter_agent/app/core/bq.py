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

"""Zero-trust caller-scoped BigQuery client resolver and safe query execution.

Architecture:
- Caller Identity Mode 1: Direct Google OAuth token forwarding (`tool_context.state`).
- Caller Identity Mode 2: Microsoft Entra ID / OIDC JWT exchange via Google Cloud STS with JWKS verification.
- Caller Identity Mode 3: Fail-closed PermissionError enforcement on user queries when missing credentials.
- Safe Query Execution: Pre-query guardrails, SELECT/WITH enforcement, dry-run cost estimation,
  maximum_bytes_billed = 5 GiB upper bound, and post-query output redaction.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from google.adk.tools import ToolContext
from google.auth import default as google_auth_default
from google.auth import identity_pool
from google.auth.transport import requests as google_requests
from google.cloud import bigquery
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials

from app.core.config import (
    AUTH_ID,
    BQ_LOCATION,
    BQ_MAX_BYTES_BILLED,
    ENTRA_CLIENT_ID,
    ENTRA_TENANT_ID,
    GCP_PROJECT_ID,
    GOOGLE_OAUTH_AUTH_CONFIG,
    OIDC_AUTH_CONFIG,
    WIF_AUDIENCE,
    is_deployed_runtime,
)
from app.core.guardrails import (
    assert_no_restricted_pay_data,
    redact_restricted_pay_fields,
)

logger = logging.getLogger(__name__)

SAFE_QUERY_PREFIX_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


class OidcJwtSupplier(identity_pool.SubjectTokenSupplier):
    """Supplies verified OIDC ID token to Google Cloud Security Token Service (STS)."""

    def __init__(self, oidc_jwt: str) -> None:
        self._jwt = oidc_jwt

    def get_subject_token(self, context: Any, request: Any) -> str:
        return self._jwt


def verify_entra_jwt(raw_jwt: str) -> dict[str, Any]:
    """Cryptographically verifies Microsoft Entra ID JWT using Microsoft's discovery JWKS keys."""
    certs_url = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/discovery/v2.0/keys"
    )
    request = google_requests.Request()
    return id_token.verify_token(
        raw_jwt,
        request,
        audience=ENTRA_CLIENT_ID,
        certs_url=certs_url,
    )


def extract_caller_google_oauth_token(tool_context: ToolContext | None) -> str | None:
    """Extracts per-user Google OAuth 2.0 access token from ToolContext."""
    if tool_context is None:
        return None
    state = getattr(tool_context, "state", None)
    short_auth_id = AUTH_ID.rsplit("/", 1)[-1] if "/" in AUTH_ID else AUTH_ID
    candidates = (
        f"temp:{AUTH_ID}",
        AUTH_ID,
        f"temp:{short_auth_id}",
        short_auth_id,
        "auth:oauth_access_token",
        "oauth_token",
        "google_access_token",
        "user_access_token",
        "access_token",
    )
    if state is not None and hasattr(state, "get"):
        for key in candidates:
            val = state.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

    if GOOGLE_OAUTH_AUTH_CONFIG is not None:
        try:
            auth_resp = tool_context.get_auth_response(GOOGLE_OAUTH_AUTH_CONFIG)
            oauth2_obj = getattr(auth_resp, "oauth2", None) if auth_resp else None
            tok = getattr(oauth2_obj, "access_token", None)
            if isinstance(tok, str) and tok.strip():
                return tok.strip()
        except Exception as exc:
            logger.debug("OAuth config retrieval failed: %s", exc)

    return None


def extract_caller_oidc_jwt(tool_context: ToolContext | None) -> str | None:
    """Extracts and optionally cryptographically validates Microsoft Entra ID / OIDC token."""
    if tool_context is None:
        return None
    state = getattr(tool_context, "state", None)
    raw_jwt: Any = state.get("auth:oidc_id_token") if hasattr(state, "get") else None
    if not (isinstance(raw_jwt, str) and raw_jwt.strip()):
        raw_jwt = None
        try:
            auth_resp = tool_context.get_auth_response(OIDC_AUTH_CONFIG)
            oauth2_obj = getattr(auth_resp, "oauth2", None) if auth_resp else None
            cand = getattr(oauth2_obj, "id_token", None)
            if isinstance(cand, str) and cand.strip():
                raw_jwt = cand.strip()
        except Exception:
            raw_jwt = None
    else:
        raw_jwt = raw_jwt.strip()

    if raw_jwt and (is_deployed_runtime() or ENTRA_TENANT_ID != "common"):
        try:
            verify_entra_jwt(raw_jwt)
        except Exception as e:
            logger.warning("JWKS verification error for Entra JWT: %s", e)
            if is_deployed_runtime():
                raise PermissionError(
                    "Failed cryptographic verification of caller OIDC JWT token."
                ) from e

    return raw_jwt


def get_caller_bq_client(
    tool_context: ToolContext | None = None,
    allow_service_account_fallback: bool = False,
) -> bigquery.Client:
    """Returns a caller-scoped BigQuery client enforcing Row-Level Security via SESSION_USER().

    Modes:
    1. Direct Google OAuth token in `tool_context.state`.
    2. Microsoft Entra ID OIDC JWT exchanged via GCP Workforce/Workload Identity Federation.
    3. Fail-closed `PermissionError` when no user token is present on RLS-protected queries
       (unless `allow_service_account_fallback=True` for non-user metadata lookups).
    """
    google_token = extract_caller_google_oauth_token(tool_context)
    if google_token:
        creds = Credentials(
            token=google_token,
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(
            project=GCP_PROJECT_ID,
            location=BQ_LOCATION,
            credentials=creds,
        )

    oidc_jwt = extract_caller_oidc_jwt(tool_context)
    if oidc_jwt:
        wif_creds = identity_pool.Credentials(
            audience=WIF_AUDIENCE,
            subject_token_type="urn:ietf:params:oauth:token-type:jwt",
            token_url="https://sts.googleapis.com/v1/token",
            subject_token_supplier=OidcJwtSupplier(oidc_jwt),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(
            project=GCP_PROJECT_ID,
            location=BQ_LOCATION,
            credentials=wif_creds,
        )

    # In deployed runtime, fail closed unless explicit service account fallback allowed for metadata
    if is_deployed_runtime() and not allow_service_account_fallback:
        raise PermissionError(
            "Access Denied: Per-user caller identity is required for Row-Level Security (RLS), "
            "but no verified user token was provided in the tool execution context. Please ensure "
            "the user is authenticated."
        )

    # Fallback to default application credentials for local development or non-user metadata lookups
    creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/bigquery"])
    return bigquery.Client(
        project=GCP_PROJECT_ID,
        location=BQ_LOCATION,
        credentials=creds,
    )


def execute_safe_sql(
    sql: str,
    tool_context: ToolContext | None = None,
    max_results: int = 500,
    allow_service_account_fallback: bool = False,
) -> list[dict[str, Any]]:
    """Executes a BigQuery query with multi-layer safety, cost enforcement, and redaction.

    Enforces:
    - Pre-query sensitive remuneration and individual pay guardrails
    - Read-only validation (query must start with SELECT or WITH)
    - BigQuery dry-run cost estimate verification
    - maximum_bytes_billed limit (5 GiB default guard)
    - Post-query payload sanitization
    """
    # 1. Pre-query guardrail check
    assert_no_restricted_pay_data(sql)

    # 2. SELECT/WITH check
    if not SAFE_QUERY_PREFIX_RE.match(sql):
        raise ValueError(
            "Security Violation: Only read-only queries starting with SELECT or WITH are permitted."
        )

    # Static SQL Advisor validation against ontology & governance policies
    from app.ontology import validate_and_advise_sql

    advisor = validate_and_advise_sql(sql)
    if not advisor.get("is_valid", True):
        issues = "; ".join(advisor.get("issues", []))
        recs = "; ".join(advisor.get("recommendations", []))
        raise ValueError(
            f"SQL Advisor Violation ({advisor.get('advisory_status')}): {issues}. Recommendations: {recs}"
        )

    client = get_caller_bq_client(
        tool_context, allow_service_account_fallback=allow_service_account_fallback
    )

    # 3. Dry-run query to estimate bytes scanned
    dry_run_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=True)
    try:
        dry_job = client.query(sql, job_config=dry_run_config)
        estimated_bytes = dry_job.total_bytes_processed or 0
        if estimated_bytes > BQ_MAX_BYTES_BILLED:
            raise ValueError(
                f"Query cost limit exceeded: Estimated query bytes ({estimated_bytes / (1024**3):.2f} GiB) "
                f"exceeds the maximum threshold ({BQ_MAX_BYTES_BILLED / (1024**3):.2f} GiB)."
            )
    except Exception as exc:
        if "Query cost limit exceeded" in str(exc):
            raise
        logger.warning("Dry-run query analysis warning: %s", exc)

    # 4. Safe execution with maximum bytes billed enforced
    exec_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=BQ_MAX_BYTES_BILLED,
        job_timeout_ms=30000,
    )
    job = client.query(sql, job_config=exec_config)
    results = job.result(max_results=max_results)

    # 5. Serialization and post-query redaction
    rows: list[dict[str, Any]] = []
    for row in results:
        item: dict[str, Any] = {}
        for k, v in dict(row).items():
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            elif isinstance(v, (int, float, str, bool, list, dict)) or v is None:
                item[k] = v
            else:
                item[k] = str(v)
        rows.append(item)

    return redact_restricted_pay_fields(rows)
