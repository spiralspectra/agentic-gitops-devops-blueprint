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

"""Three-layer sensitive remuneration, individual compensation, and PII guardrails.

Architecture:
- Layer 1 (Prompt Directive): Explicit system prompt instruction injected into all agent tiers.
- Layer 2 (Pre-Query Gate): Deterministic regex/AST gate rejecting unaggregated individual salary,
  compensation, bonus, commission, tax code, national insurance, bank account, and raw payroll queries.
- Layer 3 (Post-Query Sanitizer): Recursive payload sanitizer stripping or redacting restricted keys.
"""

from __future__ import annotations

import re
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin

RESTRICTED_PAY_PATTERN = re.compile(
    r"(?<!de)(?<!re)commission|salary|wages?|take_home|gross_pay|net_pay|pay_?rate|hourly_rate|"
    r"bonus|incentive|remunerat|payroll|pay_?period|payday|national_insurance|ni_number|ssn|social_security|"
    r"tax_code|bank_account|sort_code|iban|routing_number",
    re.IGNORECASE,
)


# Operational aggregated metrics that remain explicitly permissible
ALLOWED_AGGREGATE_PATTERN = re.compile(
    r"\b(headcount|total_fte|staff_count|department_count|active_employees_count|"
    r"avg_team_size|commission_free|decommission|recommission)\b",
    re.IGNORECASE,
)

SENSITIVE_DATA_GUARDRAIL_INSTRUCTION = """SENSITIVE REMUNERATION & INDIVIDUAL COMPENSATION GUARDRAIL (MANDATORY POLICY):
- You must NEVER query, display, estimate, rank, compare, or discuss individual colleague salary, compensation, wages, bonuses, personal commission, payroll details, tax codes, national insurance / SSN, or bank account information.
- This applies to both the signed-in user ("what is my bonus?", "calculate my commission") and other personnel ("show top earners", "what is Alex's salary?").
- Aggregated operational reporting (e.g., headcount, FTE counts, total department size, or general operational volume) is permissible.
- If asked about individual compensation or payroll data, politely decline, state that individual remuneration is restricted by organizational policy, and refer the user to their line manager or People & Payroll Operations.
"""


class RestrictedPayDataError(PermissionError):
    """Raised when an action or query targets individual compensation or restricted payroll data."""


def references_restricted_pay_data(text: str | None) -> bool:
    """Evaluates whether text or SQL targets restricted remuneration or payroll fields."""
    if not text:
        return False
    # Check if restricted pattern is matched
    for match in RESTRICTED_PAY_PATTERN.finditer(text):
        matched_str = match.group(0)
        # Verify it is not part of an allowed aggregate or benign phrasing
        if not ALLOWED_AGGREGATE_PATTERN.search(matched_str):
            return True
    return False


def is_restricted_field_name(key: Any) -> bool:
    """Checks whether a dictionary key or column name represents restricted remuneration."""
    return isinstance(key, str) and references_restricted_pay_data(key)


def assert_no_restricted_pay_data(text_or_sql: str) -> None:
    """Pre-query gate raising RestrictedPayDataError if query targets individual pay fields."""
    if references_restricted_pay_data(text_or_sql):
        raise RestrictedPayDataError(
            "Access Denied: The requested query or text references individual compensation, "
            "salary, bonus, or payroll data. Policy requires querying only approved operational "
            "and business performance views."
        )


def redact_restricted_pay_fields(payload: Any) -> Any:
    """Recursively walks dictionaries and lists, replacing restricted values with a policy marker."""
    if isinstance(payload, dict):
        sanitized: dict[str, Any] = {}
        for k, v in payload.items():
            if is_restricted_field_name(k):
                sanitized[k] = "[REDACTED_BY_POLICY]"
            else:
                sanitized[k] = redact_restricted_pay_fields(v)
        return sanitized
    if isinstance(payload, list):
        return [redact_restricted_pay_fields(item) for item in payload]
    return payload


class SafetyAndA2UIPlugin(BasePlugin):
    """ADK plugin enforcing Layer 3 post-tool redaction and request safety."""

    def __init__(self) -> None:
        super().__init__(name="safety_and_a2ui_plugin")

    async def after_tool_callback(
        self,
        *,
        tool: Any,
        tool_args: dict[str, Any],
        tool_context: Any,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        del tool, tool_args, tool_context
        if isinstance(result, dict):
            redacted = redact_restricted_pay_fields(result)
            if redacted != result:
                return redacted
        return None
