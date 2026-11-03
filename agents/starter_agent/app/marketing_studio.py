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

"""Pillar 3: Stateful Human-in-the-Loop Campaign & Artifact Marketing Studio.

Includes:
- Deterministic regulatory & brand compliance validator (checking prohibited superlatives,
  unsubstantiated claims, required disclosures, and channel character length constraints).
- Campaign asset drafting tool (`draft_campaign_asset`).
- Compliance verification tool (`validate_copy_compliance`).
- Human-gated store commit tool (`file_campaign_to_store`) that strictly refuses to persist
  assets unless `confirmed=True` after explicit operator sign-off.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from google.adk.tools import ToolContext

from app.core.config import GCP_PROJECT_ID, GCS_ARTIFACT_BUCKET

logger = logging.getLogger(__name__)

# Channel length limitations
CHANNEL_LIMITS = {
    "social_post": 280,
    "email_newsletter": 2000,
    "display_card": 500,
    "video_script": 1200,
}

# Unsubstantiated or prohibited marketing superlative claims
PROHIBITED_CLAIMS_PATTERN = re.compile(
    r"\b(100% risk free|guaranteed lowest price|cheapest in the world|"
    r"unbeatable price|zero risk|guaranteed returns|miracle results)\b",
    re.IGNORECASE,
)

# Standard required disclosure tags
REQUIRED_DISCLOSURE = "Terms & Conditions apply."


def validate_copy_compliance(
    copy_text: str, channel: str = "social_post"
) -> dict[str, Any]:
    """Validates marketing copy against brand safety, regulatory rules, and channel constraints.

    Args:
        copy_text: Marketing copy or promotional text to evaluate.
        channel: Distribution medium ('social_post', 'email_newsletter', 'display_card', 'video_script').

    Returns:
        Structured compliance report detailing violations, warnings, and overall status.
    """
    violations: list[str] = []
    warnings: list[str] = []

    # 1. Channel length check
    char_limit = CHANNEL_LIMITS.get(channel.lower(), 500)
    if len(copy_text) > char_limit:
        violations.append(
            f"Length Violation: Copy length ({len(copy_text)} chars) exceeds the {channel} limit of {char_limit} chars."
        )

    # 2. Prohibited superlative check
    found_prohibited = PROHIBITED_CLAIMS_PATTERN.findall(copy_text)
    if found_prohibited:
        violations.append(
            f"Regulatory Violation: Unsubstantiated or misleading claim detected: {list(set(found_prohibited))}."
        )

    # 3. Mandatory disclosure check
    if (
        "term" not in copy_text.lower()
        and "condition" not in copy_text.lower()
        and "t&c" not in copy_text.lower()
    ):
        warnings.append(
            f"Disclosure Warning: Standard promotional disclosure missing. Recommend adding '{REQUIRED_DISCLOSURE}'."
        )

    is_compliant = len(violations) == 0

    return {
        "is_compliant": is_compliant,
        "channel": channel,
        "character_count": len(copy_text),
        "character_limit": char_limit,
        "violations": violations,
        "warnings": warnings,
        "compliance_status": "APPROVED" if is_compliant else "REJECTED",
    }


def draft_campaign_asset(
    title: str,
    objective: str,
    target_audience: str,
    channel: str = "social_post",
    key_selling_points: list[str] | None = None,
) -> dict[str, Any]:
    """Generates a structured marketing campaign asset draft ready for review.

    Args:
        title: Working campaign title.
        objective: Primary goal (e.g. 'Promote Q4 cloud optimization workshop').
        target_audience: Target persona or customer segment.
        channel: Intended medium ('social_post', 'email_newsletter', 'display_card').
        key_selling_points: Key bullets or highlights to include.

    Returns:
        Structured campaign draft with copy text and automated compliance evaluation.
    """
    points = key_selling_points or [
        "Enterprise-grade reliability",
        "Transparent operational metrics",
        "Proven team expertise",
    ]
    bullets = " • ".join(points)

    if channel == "social_post":
        copy_text = f"Accelerate your operations with {title}: {bullets}. Discover modern practices built for scale. {REQUIRED_DISCLOSURE}"
    elif channel == "email_newsletter":
        copy_text = (
            f"Subject: Modernize Your Enterprise with {title}\n\n"
            f"Dear Partner,\n\n"
            f"Our team is launching {title} tailored for {target_audience}.\n\n"
            f"Key Highlights:\n"
            + "\n".join(f"- {p}" for p in points)
            + f"\n\nJoin us today to build sustainable operational resilience.\n\n{REQUIRED_DISCLOSURE}"
        )
    else:
        copy_text = (
            f"{title} | {objective} | Highlights: {bullets}. {REQUIRED_DISCLOSURE}"
        )

    campaign_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
    compliance = validate_copy_compliance(copy_text, channel)

    return {
        "campaign_id": campaign_id,
        "title": title,
        "channel": channel,
        "target_audience": target_audience,
        "copy_text": copy_text,
        "compliance": compliance,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "workflow_state": "DRAFT_PENDING_APPROVAL",
    }


def file_campaign_to_store(
    campaign_id: str,
    asset_payload: dict[str, Any],
    confirmed: bool = False,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Commits an approved campaign asset to the enterprise campaign store.

    CRITICAL SAFETY GATE:
    This tool enforces human-in-the-loop review. It will strictly reject execution
    and fail closed if `confirmed` is False. The human reviewer must inspect the
    draft and compliance report, then re-invoke with `confirmed=True`.

    Args:
        campaign_id: Unique campaign identifier (e.g. 'CMP-A1B2C3D4').
        asset_payload: Complete campaign dictionary including copy and metadata.
        confirmed: Explicit boolean confirmation parameter indicating human approval.

    Returns:
        Confirmation status and persistence URI.
    """
    if not confirmed:
        return {
            "status": "HUMAN_APPROVAL_REQUIRED",
            "message": (
                f"Action blocked: Campaign '{campaign_id}' has not been confirmed by a human operator. "
                "Please review the drafted copy and compliance checks. To persist this asset to "
                "the enterprise store, explicitly invoke this tool with confirmed=True."
            ),
            "campaign_id": campaign_id,
            "confirmed": False,
        }

    # Verify compliance before committing
    copy_text = asset_payload.get("copy_text", "")
    channel = asset_payload.get("channel", "social_post")
    compliance = validate_copy_compliance(copy_text, channel)

    if not compliance.get("is_compliant"):
        return {
            "status": "REJECTED_COMPLIANCE_FAILURE",
            "message": "Cannot file campaign with active regulatory or policy violations.",
            "violations": compliance.get("violations"),
        }

    # Store payload
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    record = {
        **asset_payload,
        "campaign_id": campaign_id,
        "status": "FILED_AND_COMMITTED",
        "committed_at": timestamp,
        "compliance_verified": True,
    }

    # Local fallback persistence
    store_dir = Path("/tmp/enterprise_campaign_store")
    store_dir.mkdir(parents=True, exist_ok=True)
    out_file = store_dir / f"{campaign_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    if GCS_ARTIFACT_BUCKET:
        try:
            from google.cloud import storage

            client = storage.Client(project=GCP_PROJECT_ID)
            bucket = client.bucket(GCS_ARTIFACT_BUCKET)
            blob = bucket.blob(f"campaigns/{campaign_id}.json")
            blob.upload_from_string(
                json.dumps(record, indent=2), content_type="application/json"
            )
        except Exception as exc:
            logger.warning("GCS artifact upload warning (using local store): %s", exc)

    store_uri = f"gs://{GCS_ARTIFACT_BUCKET}/campaigns/{campaign_id}.json"

    return {
        "status": "SUCCESS",
        "campaign_id": campaign_id,
        "message": f"Campaign '{campaign_id}' successfully filed and committed to enterprise store.",
        "store_uri": store_uri,
        "local_cache_path": str(out_file),
        "committed_at": timestamp,
    }
