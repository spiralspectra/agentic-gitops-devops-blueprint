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

"""Unit tests for Pillar 3 Marketing Studio regulatory and brand compliance."""

from __future__ import annotations

from app.marketing_studio import (
    CHANNEL_LIMITS,
    REQUIRED_DISCLOSURE,
    draft_campaign_asset,
    file_campaign_to_store,
    validate_copy_compliance,
)


def test_compliant_social_post():
    copy = f"Join our enterprise AI workshop to scale your systems. {REQUIRED_DISCLOSURE}"
    result = validate_copy_compliance(copy, channel="social_post")
    assert result["is_compliant"] is True
    assert result["compliance_status"] == "APPROVED"
    assert result["violations"] == []


def test_channel_length_limit_exceeded():
    limit = CHANNEL_LIMITS["social_post"]
    long_copy = "A" * (limit + 10) + f" {REQUIRED_DISCLOSURE}"
    result = validate_copy_compliance(long_copy, channel="social_post")
    assert result["is_compliant"] is False
    assert result["compliance_status"] == "REJECTED"
    assert any("Length Violation" in v for v in result["violations"])


def test_prohibited_claims_detected():
    copy = f"Get our new plan with guaranteed lowest price and zero risk! {REQUIRED_DISCLOSURE}"
    result = validate_copy_compliance(copy, channel="social_post")
    assert result["is_compliant"] is False
    assert any("Regulatory Violation" in v for v in result["violations"])


def test_missing_disclosure_warning():
    copy = "Accelerate your infrastructure today with automated scaling."
    result = validate_copy_compliance(copy, channel="social_post")
    # Missing disclosure produces warning, but does not block compliance if no violations
    assert result["is_compliant"] is True
    assert any("Disclosure Warning" in w for w in result["warnings"])


def test_draft_campaign_asset():
    draft = draft_campaign_asset(
        title="Modern Cloud Operations",
        objective="Drive Q4 registrations",
        target_audience="DevOps Engineers",
        channel="social_post",
    )
    assert draft["campaign_id"].startswith("CMP-")
    assert draft["channel"] == "social_post"
    assert draft["workflow_state"] == "DRAFT_PENDING_APPROVAL"
    assert "compliance" in draft


def test_file_campaign_blocks_without_human_confirmation():
    payload = {
        "copy_text": f"Modernize with resilience. {REQUIRED_DISCLOSURE}",
        "channel": "social_post",
    }
    res = file_campaign_to_store("CMP-TEST1234", payload, confirmed=False)
    assert res["status"] == "HUMAN_APPROVAL_REQUIRED"
    assert res["confirmed"] is False
    assert "Action blocked" in res["message"]


def test_file_campaign_commits_with_human_confirmation(tmp_path):
    payload = {
        "copy_text": f"Modernize with resilience. {REQUIRED_DISCLOSURE}",
        "channel": "social_post",
    }
    res = file_campaign_to_store("CMP-TEST5678", payload, confirmed=True)
    assert res["status"] == "SUCCESS"
    assert res["campaign_id"] == "CMP-TEST5678"
    assert "store_uri" in res


def test_file_campaign_rejects_non_compliant_copy_even_if_confirmed():
    payload = {
        "copy_text": "Sign up for guaranteed lowest price miracle results!",
        "channel": "social_post",
    }
    res = file_campaign_to_store("CMP-FAIL1234", payload, confirmed=True)
    assert res["status"] == "REJECTED_COMPLIANCE_FAILURE"
    assert "violations" in res
