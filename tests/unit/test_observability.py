# Copyright 2026 Google LLC
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

"""Unit tests for telemetry, logging, and latency recording."""

from __future__ import annotations

import uuid


def format_telemetry_event(session_id: str, query: str, duration_ms: float) -> dict:
    """Formats structured telemetry log event for BigQuery / Cloud Logging."""
    return {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "query_length": len(query),
        "duration_ms": duration_ms,
        "status": "success" if duration_ms < 5000.0 else "slow",
    }


def test_telemetry_formatting():
    session_id = str(uuid.uuid4())
    event = format_telemetry_event(session_id, "Test query", 120.5)

    assert event["session_id"] == session_id
    assert event["query_length"] == 10
    assert event["duration_ms"] == 120.5
    assert event["status"] == "success"


def test_slow_query_flagging():
    session_id = str(uuid.uuid4())
    event = format_telemetry_event(session_id, "Heavy query", 6200.0)

    assert event["status"] == "slow"
