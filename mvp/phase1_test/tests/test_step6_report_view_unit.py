"""
Unit tests for Step6 Report Aggregation.

Tests aggregate_report() function with minimal mock inputs.
Validates:
- All required top-level keys exist
- scores.overall is number 0-100
- warnings is list with {code, message?} items
- report_view has chart_data + highlights; both are lists
- highlights sorted by (start_ms, end_ms, type, text_snippet)
- No forbidden keys: evidence_refs, rule_id, root next_target
"""

import pytest

from app.pipeline.step6_report_aggregation import aggregate_report


# Minimal mock inputs for testing
_MOCK_STEP1_ASR = {
    "ok": True,
    "error_reason": None,
    "asr": {
        "transcript": "测试文本",
        "segments": [
            {"start_ms": 0, "end_ms": 2000, "text": "测试", "confidence": 0.9},
            {"start_ms": 2000, "end_ms": 5000, "text": "文本", "confidence": 0.8},
        ],
        "overall_confidence": 0.85,
    },
}

_MOCK_STEP2_PACE_PAUSE = {
    "pause_segments": [
        {"start_ms": 1000, "end_ms": 1500, "duration_ms": 500},
    ],
    "long_pause_count": 0,
    "max_pause_ms": 500,
    "pace_series": [
        {"t_ms": 0, "speech_ms": 1000},
        {"t_ms": 1000, "speech_ms": 500},
        {"t_ms": 2000, "speech_ms": 1000},
    ],
    "wpm": 60.0,
    "speaking_rate_cpm": 120.0,
}

_MOCK_STEP4_REPORT = {
    "pol_version": "POL-v0.1",
    "session": {
        "session_id": "test-session-id",
        "task_type": "IMPROV_60S",
        "language": "zh",
        "generated_at": "2026-03-03T00:00:00+00:00",
    },
    "rule_engine": {
        "triggers": [
            {
                "id": "BR-OPP-001-R-TASK-001",
                "severity": "P1",
                "impact_score": 0.6,
                "weight": 1.0,
                "priority_score": 0.6,
                "conflict_priority": 2,
                "trigger_count": 1,
                "evidence": {
                    "time_ranges": [{"start_ms": 0, "end_ms": 5000}],
                    "text_snippets": ["测试文本"],
                },
            },
        ],
        "top_trigger_id": "BR-OPP-001-R-TASK-001",
        "next_target": None,
    },
    "warnings": [],
}

_MOCK_STEP5_REPORT = {
    "pol_version": "POL-v0.1",
    "session": {
        "session_id": "test-session-id",
        "task_type": "IMPROV_60S",
        "language": "zh",
        "generated_at": "2026-03-03T00:00:00+00:00",
    },
    "rule_engine": {
        "triggers": [
            {
                "id": "BR-OPP-001-R-TASK-001",
                "severity": "P1",
                "impact_score": 0.6,
                "weight": 1.0,
                "priority_score": 0.6,
                "conflict_priority": 2,
                "trigger_count": 1,
                "evidence": {
                    "time_ranges": [{"start_ms": 0, "end_ms": 5000}],
                    "text_snippets": ["测试文本"],
                },
            },
        ],
        "top_trigger_id": "BR-OPP-001-R-TASK-001",
        "next_target": None,
    },
    "llm_feedback": {
        "suggestions": [
            {
                "id": "sugg-001",
                "title": "改进建议",
                "content": "测试建议内容",
                "evidence_ref": {
                    "time_ranges": [{"start_ms": 0, "end_ms": 5000}],
                    "text_snippets": ["测试文本"],
                },
            },
        ],
    },
    "warnings": [],
}


def _scan_for_forbidden_keys(obj, path=""):
    """
    Recursively scan for forbidden keys.

    Forbidden:
    - evidence_refs (any path)
    - rule_id (any path)
    - next_target at root level

    Returns list of violations.
    """
    violations = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # Check for forbidden keys
            if key == "evidence_refs":
                violations.append(f"Forbidden key 'evidence_refs' at {current_path}")
            if key == "rule_id":
                violations.append(f"Forbidden key 'rule_id' at {current_path}")

            # Recurse
            violations.extend(_scan_for_forbidden_keys(value, current_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(_scan_for_forbidden_keys(item, f"{path}[{i}]"))

    return violations


def _check_root_next_target(obj):
    """Check if next_target exists at root level."""
    if isinstance(obj, dict):
        if "next_target" in obj:
            return True
    return False


class TestStep6AggregateReport:
    """Test suite for aggregate_report()."""

    def test_required_top_level_keys_exist(self):
        """All required top-level keys must exist."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        required_keys = {
            "pol_version",
            "session",
            "scores",
            "rule_engine",
            "llm_feedback",
            "report_view",
            "warnings",
        }

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_scores_overall_is_number_0_to_100(self):
        """scores.overall must be a number in range 0-100."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        overall = result["scores"]["overall"]
        assert isinstance(overall, (int, float)), "scores.overall must be a number"
        assert 0 <= overall <= 100, f"scores.overall={overall} out of range [0, 100]"

    def test_warnings_is_list_with_code_items(self):
        """warnings must be a list; each item is dict with 'code' field."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        warnings = result["warnings"]
        assert isinstance(warnings, list), "warnings must be a list"

        for w in warnings:
            assert isinstance(w, dict), "Each warning item must be a dict"
            assert "code" in w, "Each warning item must have 'code' field"

    def test_report_view_has_chart_data_and_highlights(self):
        """report_view must have chart_data and highlights; both are objects."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        report_view = result["report_view"]
        assert isinstance(report_view, dict), "report_view must be a dict"
        assert "chart_data" in report_view, "report_view missing chart_data"
        assert "highlights" in report_view, "report_view missing highlights"

    def test_chart_data_has_pace_and_pause_series(self):
        """chart_data must have pace_series and pause_series; both are lists."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        chart_data = result["report_view"]["chart_data"]
        assert isinstance(chart_data, dict), "chart_data must be a dict"

        pace_series = chart_data.get("pace_series")
        pause_series = chart_data.get("pause_series")

        assert isinstance(pace_series, list), "pace_series must be a list"
        assert isinstance(pause_series, list), "pause_series must be a list"

    def test_highlights_sorted_by_start_ms_end_ms(self):
        """highlights must be sorted by (start_ms, end_ms, type, text_snippet)."""
        # Create mock with multiple triggers to test sorting
        mock_step4 = {
            "rule_engine": {
                "triggers": [
                    {
                        "id": "trigger-b",
                        "severity": "P1",
                        "evidence": {
                            "time_ranges": [{"start_ms": 5000, "end_ms": 10000}],
                            "text_snippets": ["later text"],
                        },
                    },
                    {
                        "id": "trigger-a",
                        "severity": "P0",
                        "evidence": {
                            "time_ranges": [{"start_ms": 0, "end_ms": 2000}],
                            "text_snippets": ["earlier text"],
                        },
                    },
                ],
                "top_trigger_id": "trigger-b",
                "next_target": None,
            },
            "warnings": [],
        }

        mock_step5 = {
            "rule_engine": mock_step4["rule_engine"],
            "llm_feedback": {"suggestions": []},
            "warnings": [],
        }

        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=mock_step4,
            step5_llm_feedback=mock_step5,
        )

        highlights = result["report_view"]["highlights"]
        assert len(highlights) >= 2, "Should have at least 2 highlights"

        # Verify sorted order
        for i in range(1, len(highlights)):
            prev = highlights[i - 1]
            curr = highlights[i]

            prev_key = (prev["start_ms"], prev["end_ms"], prev["type"], prev["text_snippet"])
            curr_key = (curr["start_ms"], curr["end_ms"], curr["type"], curr["text_snippet"])

            assert prev_key <= curr_key, f"Highlights not sorted: {prev_key} > {curr_key}"

    def test_no_forbidden_keys_evidence_refs_rule_id(self):
        """No forbidden keys: evidence_refs, rule_id anywhere in output."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        violations = _scan_for_forbidden_keys(result)
        assert len(violations) == 0, f"Forbidden keys found: {violations}"

    def test_no_root_level_next_target(self):
        """next_target must NOT exist at root level."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        has_root_next_target = _check_root_next_target(result)
        assert not has_root_next_target, "Root-level next_target is forbidden"

    def test_empty_triggers_overall_score(self):
        """Test overall score with empty triggers (should be base=90)."""
        mock_step4_empty = {
            "rule_engine": {
                "triggers": [],
                "top_trigger_id": None,
                "next_target": None,
            },
            "warnings": [],
        }

        mock_step5_empty = {
            "rule_engine": mock_step4_empty["rule_engine"],
            "llm_feedback": {"suggestions": []},
            "warnings": [],
        }

        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=mock_step4_empty,
            step5_llm_feedback=mock_step5_empty,
        )

        assert result["scores"]["overall"] == 90, "Empty triggers should give overall=90"

    def test_p0_severity_penalty(self):
        """Test P0 severity penalty (base=90, penalty=30, overall=60)."""
        mock_step4_p0 = {
            "rule_engine": {
                "triggers": [
                    {
                        "id": "trigger-p0",
                        "severity": "P0",
                        "evidence": {
                            "time_ranges": [],
                            "text_snippets": [],
                        },
                    },
                ],
                "top_trigger_id": "trigger-p0",
                "next_target": None,
            },
            "warnings": [],
        }

        mock_step5_p0 = {
            "rule_engine": mock_step4_p0["rule_engine"],
            "llm_feedback": {"suggestions": []},
            "warnings": [],
        }

        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=mock_step4_p0,
            step5_llm_feedback=mock_step5_p0,
        )

        # base=90, P0 penalty=30, no extra -> overall=60
        assert result["scores"]["overall"] == 60, "P0 trigger should give overall=60"

    def test_multiple_triggers_extra_penalty(self):
        """Test multiple triggers extra penalty."""
        mock_step4_multi = {
            "rule_engine": {
                "triggers": [
                    {"id": "t1", "severity": "P2", "evidence": {"time_ranges": [], "text_snippets": []}},
                    {"id": "t2", "severity": "P2", "evidence": {"time_ranges": [], "text_snippets": []}},
                    {"id": "t3", "severity": "P2", "evidence": {"time_ranges": [], "text_snippets": []}},
                ],
                "top_trigger_id": "t1",
                "next_target": None,
            },
            "warnings": [],
        }

        mock_step5_multi = {
            "rule_engine": mock_step4_multi["rule_engine"],
            "llm_feedback": {"suggestions": []},
            "warnings": [],
        }

        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=mock_step4_multi,
            step5_llm_feedback=mock_step5_multi,
        )

        # base=90, P2 penalty=8, extra=(3-1)*3=6 -> overall=90-8-6=76
        assert result["scores"]["overall"] == 76, "3 triggers should give overall=76"

    def test_missing_step2_degrades_gracefully(self):
        """Test that missing Step2 result degrades gracefully."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=None,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        chart_data = result["report_view"]["chart_data"]
        assert chart_data["pace_series"] == [], "Missing Step2 should give empty pace_series"
        assert chart_data["pause_series"] == [], "Missing Step2 should give empty pause_series"

    def test_session_fields_exist(self):
        """Test that session has all required fields."""
        result = aggregate_report(
            step1_asr=_MOCK_STEP1_ASR,
            step2_pace_pause=_MOCK_STEP2_PACE_PAUSE,
            step4_rule_engine=_MOCK_STEP4_REPORT,
            step5_llm_feedback=_MOCK_STEP5_REPORT,
        )

        session = result["session"]
        assert "session_id" in session
        assert "task_type" in session
        assert "language" in session
        assert "generated_at" in session

        assert session["task_type"] == "IMPROV_60S"
        assert session["language"] == "zh"
