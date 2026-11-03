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

import json
import tempfile
from pathlib import Path

import pytest

from tests.eval import check_thresholds
from tests.eval.check_thresholds import (
    POLICY_COMPLIANCE_METRIC,
    RESPONSE_QUALITY_METRIC,
    SAFETY_GUARDRAIL_METRIC,
    TOOL_GROUNDING_METRIC,
    CaseRow,
    Thresholds,
    evaluate,
    find_latest_results,
    render_markdown_summary,
    write_step_summary,
)


def _results(cases: list[dict], case_ids: list[str] | None = None) -> dict:
    """Builds an eval results dict in the format agents-cli eval grade writes."""
    eval_case_results = []
    for i, metrics in enumerate(cases):
        metric_results = {}
        for name, value in metrics.items():
            if isinstance(value, dict):
                metric_results[name] = {"metric_name": name, **value}
            else:
                metric_results[name] = {"metric_name": name, "score": value}
        eval_case_results.append(
            {
                "eval_case_index": i,
                "response_candidate_results": [
                    {"response_index": 0, "metric_results": metric_results}
                ],
            }
        )
    dataset = [{"eval_case_id": cid} for cid in (case_ids or [])]
    return {
        "eval_case_results": eval_case_results,
        "summary_metrics": [
            {"metric_name": RESPONSE_QUALITY_METRIC},
            {"metric_name": TOOL_GROUNDING_METRIC},
        ],
        "metadata": {"dataset": dataset},
    }


def _good_case(score: float = 0.90) -> dict:
    return {
        RESPONSE_QUALITY_METRIC: score,
        TOOL_GROUNDING_METRIC: 1.0,
        SAFETY_GUARDRAIL_METRIC: 1.0,
        POLICY_COMPLIANCE_METRIC: 1.0,
        "agent_turn_count": 3,
    }


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


def test_passes_when_all_cases_meet_the_bar():
    results = _results([_good_case(0.95), _good_case(0.85), _good_case(0.80)], ["c1", "c2", "c3"])
    failures, rows = evaluate(results, Thresholds())
    assert failures == []
    assert [r.case_id for r in rows] == ["c1", "c2", "c3"]


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


def test_fails_on_single_bad_case_even_if_mean_is_fine():
    results = _results(
        [_good_case(1.0), _good_case(1.0), _good_case(0.20)],
        ["p1", "p2", "p3_failing"],
    )
    failures, _ = evaluate(results, Thresholds(min_case_score=0.50))
    assert any("below floor" in f or "p3_failing" in f for f in failures)


def test_fails_when_a_case_did_not_call_a_domain_tool():
    bad = _good_case(0.90)
    bad[TOOL_GROUNDING_METRIC] = 0.0
    results = _results([_good_case(0.90), bad], ["ok_case", "no_tool_case"])
    failures, _ = evaluate(results, Thresholds(min_tool_grounding_rate=1.0))
    assert any("Tool grounding" in f or "no_tool_case" in f for f in failures)


def test_tool_grounding_threshold_is_configurable():
    bad = _good_case(0.90)
    bad[TOOL_GROUNDING_METRIC] = 0.0
    results = _results([_good_case(0.90), _good_case(0.90), _good_case(0.90), bad])
    thresholds = Thresholds(min_tool_grounding_rate=0.70)
    failures, _ = evaluate(results, thresholds)
    assert failures == []


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


def test_fails_on_empty_evals():
    failures, rows = evaluate([], Thresholds())
    assert len(failures) > 0
    assert any("No evaluation results" in f for f in failures)
    assert len(rows) == 0


def test_thresholds_from_env(monkeypatch: pytest.MonkeyPatch):
    env = {
        "EVAL_MIN_MEAN_RESPONSE_QUALITY": "4.2",
        "EVAL_MIN_CASE_RESPONSE_QUALITY": "3",
        "EVAL_MIN_TOOL_GROUNDING_RATE": "0.85",
        "EVAL_MIN_POLICY_COMPLIANCE_RATE": "0.95",
        "EVAL_MIN_SAFETY_GUARDRAIL_RATE": "1.0",
        "EVAL_MAX_ERRORED_CASES": "2",
    }
    t = Thresholds.from_env_or_config(env=env)
    assert t.min_mean_score == pytest.approx(4.2 / 5.0)
    assert t.min_case_score == pytest.approx(3.0 / 5.0)
    assert t.min_tool_grounding_rate == 0.85
    assert t.min_policy_compliance_rate == 0.95
    assert t.min_safety_guardrail_rate == 1.0
    assert t.max_errored_cases == 2


def test_find_latest_results_in_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        find_latest_results(tmp_path)

    f1 = tmp_path / "results_20260101_100000.json"
    f1.write_text("{}", encoding="utf-8")
    f2 = tmp_path / "results_20260102_100000.json"
    f2.write_text("{}", encoding="utf-8")

    latest = find_latest_results(tmp_path)
    assert latest.name == "results_20260102_100000.json"


def test_main_cli_positional_and_flag_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    good_results = [_good_case(0.90)]
    f = tmp_path / "eval_results.json"
    f.write_text(json.dumps(good_results), encoding="utf-8")

    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    # Test with positional argument
    rc_pos = check_thresholds.main([str(f)])
    assert rc_pos == 0
    assert "Agent Evaluation Quality Gate" in summary_file.read_text(encoding="utf-8")

    # Test with --results-file
    rc_flag = check_thresholds.main(["--results-file", str(f)])
    assert rc_flag == 0

    # Test with --results-dir
    rc_dir = check_thresholds.main(["--results-dir", str(tmp_path)])
    assert rc_dir == 0


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
