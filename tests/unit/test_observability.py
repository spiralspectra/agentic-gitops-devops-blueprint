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

"""Unit tests for telemetry, logging, and latency recording."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

APP_INIT = Path(__file__).resolve().parents[2] / "agents" / "starter_agent" / "app" / "__init__.py"
APP_FILE = (
    APP_INIT
    if APP_INIT.is_file()
    else Path(__file__).resolve().parents[2] / "agents" / "starter_agent" / "app.py"
)
_spec = importlib.util.spec_from_file_location("starter_agent_standalone_app", APP_FILE)
assert _spec and _spec.loader
_starter_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_starter_app)
format_telemetry_event = _starter_app.format_telemetry_event


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
