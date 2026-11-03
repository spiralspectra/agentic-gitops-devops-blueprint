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

"""12-Factor centralized configuration module for enterprise agent runtime."""

from __future__ import annotations

import datetime
import os
import re
import socket

import certifi
import urllib3.util.connection
from google.adk.auth import (
    AuthConfig,
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
    OpenIdConnectWithConfig,
)
from google.genai import types

os.environ.setdefault("SSL_CERT_FILE", certifi.where())


def is_deployed_runtime() -> bool:
    """Returns True when running inside Cloud Run or Vertex AI Agent Engine."""
    return bool(os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID"))


def enable_local_dev_shims() -> bool:
    """Returns True in local developer environments when shims are active."""
    if is_deployed_runtime():
        return False
    raw = os.getenv("ENABLE_LOCAL_DEV_SHIMS", "auto").strip().lower()
    return raw not in ("0", "false", "no", "off")


# Enable IPv4 resolution over IPv6 stalls in restricted local environments
if enable_local_dev_shims():
    urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

# Core GCP / Vertex AI Agent Engine parameters
GCP_PROJECT_ID = (
    os.getenv("GCP_PROJECT_ID", "").strip()
    or os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    or "enterprise-agent-project"
)
GCP_REGION = os.getenv("GCP_REGION", "").strip() or os.getenv(
    "GOOGLE_CLOUD_LOCATION", "us-central1"
)
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "").strip() or GCP_PROJECT_ID

# Model Configuration (Gemini 2.5 architecture)
AGENT_ROUTER_MODEL = os.getenv("AGENT_ROUTER_MODEL", "gemini-2.5-flash")
AGENT_PILLAR_MODEL = (
    os.getenv("AGENT_PILLAR_MODEL") or os.getenv("AGENT_CORE_MODEL") or "gemini-2.5-pro"
)

# BigQuery & Storage
BQ_DATASET_ID = (
    os.getenv("BQ_DATASET_ID")
    or os.getenv("BQ_DATASET")
    or os.getenv("APP_BQ_DATASET")
    or "lakehouse_sharing"
)
BQ_LOCATION = os.getenv("BQ_LOCATION") or os.getenv("APP_BQ_LOCATION") or GCP_REGION
BQ_MAX_BYTES_BILLED = int(
    os.getenv("BQ_MAX_BYTES_BILLED", str(5 * 1024**3))
)  # 5 GiB default guard
GCS_ARTIFACT_BUCKET = os.getenv(
    "GCS_ARTIFACT_BUCKET", f"{GCP_PROJECT_ID}-agent-artifacts"
)

# Interactive A2UI WebFrame Configuration
A2UI_IFRAME_BASE_URL = os.getenv("A2UI_IFRAME_BASE_URL", "https://a2ui.example.com")

# Workload / Workforce Identity Federation (WIF) & Microsoft Entra ID OIDC
WIF_POOL_ID = os.getenv("WIF_POOL_ID", "enterprise-oidc-pool")
WIF_PROVIDER_ID = os.getenv("WIF_PROVIDER_ID", "entra-oidc-provider")
ENTRA_TENANT_ID = os.getenv("ENTRA_TENANT_ID", "common")
ENTRA_CLIENT_ID = os.getenv("ENTRA_CLIENT_ID", "api://enterprise-gemini-agent")

WIF_AUDIENCE = os.getenv(
    "WIF_AUDIENCE",
    f"//iam.googleapis.com/locations/global/workforcePools/{WIF_POOL_ID}/providers/{WIF_PROVIDER_ID}",
)

# Per-user OAuth Authorization for BigQuery
AUTH_ID = os.getenv("AGENT_AUTH_ID", "enterprise-bigquery-oauth")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "").strip()
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "").strip()

GOOGLE_OAUTH_AUTH_CONFIG: AuthConfig | None = (
    AuthConfig(
        auth_scheme=OpenIdConnectWithConfig(
            openIdConnectUrl="https://accounts.google.com/.well-known/openid-configuration",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            scopes=["openid", "email", "https://www.googleapis.com/auth/bigquery"],
        ),
        raw_auth_credential=AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2,
            oauth2=OAuth2Auth(
                client_id=OAUTH_CLIENT_ID,
                client_secret=OAUTH_CLIENT_SECRET,
            ),
        ),
        credential_key="google_bigquery_oauth",
    )
    if OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET
    else None
)

OIDC_AUTH_CONFIG = AuthConfig(
    auth_scheme=OpenIdConnectWithConfig(
        openIdConnectUrl=(
            f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0/.well-known/openid-configuration"
        ),
        authorization_endpoint=(
            f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2.0/authorize"
        ),
        token_endpoint=(
            f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2.0/token"
        ),
    )
)

# Demo Date Anchor for deterministic evaluation
SNAPSHOT_ANCHOR_DATE = os.getenv("DEMO_ANCHOR_DATE", "2026-10-17")

# Inference Generation Profiles
ROUTER_MODEL_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
    temperature=0.1,
)
PILLAR_MODEL_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="MEDIUM"),
    temperature=0.2,
)
MODEL_CONFIG = PILLAR_MODEL_CONFIG


def normalize_date(
    raw_date: str | None,
    default_date: str = SNAPSHOT_ANCHOR_DATE,
    allow_all: bool = False,
) -> str:
    """Anchors relative date expressions to the active evaluation snapshot date."""
    cleaned = (raw_date or "").strip()
    upper = cleaned.upper()
    if allow_all and upper in ("", "ALL", "ANY", "*"):
        return "ALL"
    if not cleaned or upper in (
        "TODAY",
        "NOW",
        "CURRENT_DATE",
        "THIS MONDAY",
        "MONDAY",
        "THIS WEEK",
    ):
        return default_date

    anchor_dt = datetime.date.fromisoformat(SNAPSHOT_ANCHOR_DATE)
    if upper in ("YESTERDAY", "T-1", "1WD", "LAST WORK DAY"):
        return (anchor_dt - datetime.timedelta(days=1)).isoformat()

    m_minus = re.match(r"^T-(\d+)$", upper)
    if m_minus:
        return (anchor_dt - datetime.timedelta(days=int(m_minus.group(1)))).isoformat()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        try:
            return datetime.date.fromisoformat(cleaned).isoformat()
        except ValueError:
            return default_date

    return default_date


def normalize_scope_filter(raw_val: str | None) -> str:
    """Normalizes optional department, location, or user identifier filter values."""
    cleaned = (raw_val or "").strip()
    if not cleaned or cleaned.upper() in ("ALL", "ANY", "*"):
        return "ALL"
    return cleaned
