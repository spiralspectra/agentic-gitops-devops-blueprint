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

"""Unit tests for check_thresholds evaluation quality gate."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.eval.check_thresholds import (
    RESPONSE_QUALITY_METRIC,
    SAFETY_GUARDRAIL_METRIC,
    CaseRow,
    Thresholds,
    evaluate,
    render_markdown_summary,
    write_step_summary,
)


def test_passing_suite():
    thresholds = Thresholds(
        min_mean_score=0.75,
        min_case_score=0.50,
        min_safety_guardrail_rate=1.00,
        max_errored_cases=0,
    )
    results = [
        {
            "eval_case_id": "case_1",
            "score": 0.90,
            "metrics": {
                RESPONSE_QUALITY_METRIC: {"score": 0.90},
                SAFETY_GUARDRAIL_METRIC: {"score": 1.00},
            },
        },
        {
            "eval_case_id": "case_2",
            "score": 0.80,
            "metrics": {
                RESPONSE_QUALITY_METRIC: {"score": 0.80},
                SAFETY_GUARDRAIL_METRIC: {"score": 1.00},
            },
        },
    ]
    failures, rows = evaluate(results, thresholds)
    assert not failures
    assert len(rows) == 2


def test_mean_below_floor():
    thresholds = Thresholds(min_mean_score=0.80)
    results = [
        {
            "eval_case_id": "case_1",
            "metrics": {RESPONSE_QUALITY_METRIC: {"score": 0.70}},
        },
        {
            "eval_case_id": "case_2",
            "metrics": {RESPONSE_QUALITY_METRIC: {"score": 0.75}},
        },
    ]
    failures, _ = evaluate(results, thresholds)
    assert any("Mean score" in f for f in failures)


def test_single_case_below_floor():
    thresholds = Thresholds(min_case_score=0.50)
    results = [
        {
            "eval_case_id": "case_1",
            "metrics": {RESPONSE_QUALITY_METRIC: {"score": 0.90}},
        },
        {
            "eval_case_id": "case_failing",
            "metrics": {RESPONSE_QUALITY_METRIC: {"score": 0.40}},
        },
    ]
    failures, _ = evaluate(results, thresholds)
    assert any("Cases below floor" in f for f in failures)


def test_safety_guardrail_failure():
    thresholds = Thresholds(min_safety_guardrail_rate=1.00)
    results = [
        {
            "eval_case_id": "guardrail_1",
            "metrics": {SAFETY_GUARDRAIL_METRIC: {"score": 0.00}},
        }
    ]
    failures, _ = evaluate(results, thresholds)
    assert any("Safety guardrail rate" in f for f in failures)


def test_errored_case_failure():
    thresholds = Thresholds(max_errored_cases=0)
    results = [
        {
            "eval_case_id": "case_error",
            "errors": {"tool_call": "TimeoutError connecting to backend"},
        }
    ]
    failures, _ = evaluate(results, thresholds)
    assert any("metric errors" in f for f in failures)


def test_markdown_and_step_summary_generation(monkeypatch):
    thresholds = Thresholds()
    rows = [
        CaseRow(
            case_id="case_1",
            scores={RESPONSE_QUALITY_METRIC: 0.95, SAFETY_GUARDRAIL_METRIC: 1.0},
        )
    ]
    summary_md = render_markdown_summary("test_results.json", rows, [], thresholds)
    assert "Agent Evaluation Quality Gate" in summary_md
    assert "case_1" in summary_md

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        step_summary_path = tf.name

    monkeypatch.setenv("GITHUB_STEP_SUMMARY", step_summary_path)
    write_step_summary(summary_md)

    content = Path(step_summary_path).read_text(encoding="utf-8")
    assert "Agent Evaluation Quality Gate" in content
    Path(step_summary_path).unlink(missing_ok=True)
