"""Unit tests for LLM fallback functionality."""

import os
from pathlib import Path

from app.pipeline.step5_llm_feedback import step5_llm_feedback
from app.llm.template_fallback import (
    build_fallback_suggestions,
    build_template_suggestion,
    get_drill_id,
    is_known_rule_id,
    RULE_TO_DRILL_MAP
)
from app.llm.schema_validate import validate_suggestions, DRILL_ID_ALLOWLIST
from app.llm.trace import get_trace_file


def _create_minimal_report(top_trigger_id: str, triggers: list | None = None) -> dict:
    """Create a minimal report for testing."""
    if triggers is None and top_trigger_id:
        triggers = [
            {
                "id": top_trigger_id,
                "severity": "P0",
                "impact_score": 0.5,
                "weight": 1.0,
                "priority_score": 0.5,
                "conflict_priority": 1,
                "trigger_count": 1,
                "evidence": {
                    "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                    "text_snippets": ["test snippet"],
                },
            }
        ]
    
    return {
        "pol_version": "POL-v0.1",
        "session": {
            "session_id": "test-session",
            "task_type": "IMPROV_60S",
            "language": "zh",
            "generated_at": "2026-03-01T00:00:00Z",
        },
        "scores": {"overall": 80},
        "rule_engine": {
            "triggers": triggers or [],
            "top_trigger_id": top_trigger_id,
            "next_target": None,
        },
        "llm_feedback": {"suggestions": []},
        "warnings": [],
    }


def test_case1_no_api_key_fallback() -> None:
    """
    Case 1: No API key -> step5_llm_feedback must use template fallback.
    
    Validates:
    - suggestions length = 1 (when top_trigger_id != null)
    - suggestion has all required fields
    - warnings include LLM_UNAVAILABLE and PARTIAL_REPORT
    """
    report = _create_minimal_report("BR-OPP-001-R-TASK-001")
    
    result = step5_llm_feedback(report)
    
    # Check suggestions
    suggestions = result["llm_feedback"]["suggestions"]
    assert len(suggestions) == 1, f"Expected 1 suggestion, got {len(suggestions)}"
    
    suggestion = suggestions[0]
    
    # Check required fields exist
    required_fields = {"title", "problem", "cause", "evidence_ref", "drill", "acceptance"}
    assert required_fields.issubset(suggestion.keys()), f"Missing fields: {required_fields - set(suggestion.keys())}"
    
    # Check evidence_ref structure
    evidence_ref = suggestion["evidence_ref"]
    assert "time_ranges" in evidence_ref, "evidence_ref must have time_ranges"
    assert "text_snippets" in evidence_ref, "evidence_ref must have text_snippets"
    
    # Check drill structure
    drill = suggestion["drill"]
    assert "drill_id" in drill, "drill must have drill_id"
    assert drill["drill_id"] in DRILL_ID_ALLOWLIST, f"drill_id '{drill['drill_id']}' not in allowlist"
    assert "steps" in drill, "drill must have steps"
    assert "duration_sec" in drill, "drill must have duration_sec"
    assert "tips" in drill, "drill must have tips"
    
    # Check acceptance structure
    acceptance = suggestion["acceptance"]
    assert "metric" in acceptance, "acceptance must have metric"
    assert "target" in acceptance, "acceptance must have target"
    assert "how_to_measure" in acceptance, "acceptance must have how_to_measure"
    
    # Check warnings
    warnings = result["warnings"]
    assert "LLM_UNAVAILABLE" in warnings, "warnings must include LLM_UNAVAILABLE"
    assert "PARTIAL_REPORT" in warnings, "warnings must include PARTIAL_REPORT"


def test_case2_empty_triggers() -> None:
    """
    Case 2: triggers=[] -> suggestions=[] and warnings include NO_TRIGGERS.
    """
    report = _create_minimal_report(top_trigger_id=None, triggers=[])
    
    result = step5_llm_feedback(report)
    
    # Check suggestions is empty
    suggestions = result["llm_feedback"]["suggestions"]
    assert suggestions == [], f"Expected empty suggestions, got {suggestions}"
    
    # Check warnings
    warnings = result["warnings"]
    assert "NO_TRIGGERS" in warnings, "warnings must include NO_TRIGGERS"


def test_case3_empty_evidence() -> None:
    """
    Case 3: evidence both arrays empty -> warnings include LOW_EVIDENCE_CONFIDENCE + PARTIAL_REPORT.
    """
    triggers = [
        {
            "id": "BR-OPP-001-R-TASK-001",
            "severity": "P0",
            "impact_score": 0.5,
            "weight": 1.0,
            "priority_score": 0.5,
            "conflict_priority": 1,
            "trigger_count": 1,
            "evidence": {
                "time_ranges": [],  # Empty
                "text_snippets": [],  # Empty
            },
        }
    ]
    report = _create_minimal_report("BR-OPP-001-R-TASK-001", triggers)
    
    result = step5_llm_feedback(report)
    
    # Check suggestions exists (fallback should still produce one)
    suggestions = result["llm_feedback"]["suggestions"]
    assert len(suggestions) == 1, f"Expected 1 suggestion, got {len(suggestions)}"
    
    # Check warnings
    warnings = result["warnings"]
    assert "LOW_EVIDENCE_CONFIDENCE" in warnings, "warnings must include LOW_EVIDENCE_CONFIDENCE"
    assert "PARTIAL_REPORT" in warnings, "warnings must include PARTIAL_REPORT"


def test_template_suggestion_structure() -> None:
    """
    Test that template suggestion has correct structure for all rule types.
    """
    rule_ids = [
        "BR-OPP-001-R-TASK-001",
        "BR-OPP-001-R-STRUCT-001",
        "BR-OPP-001-R-SPEED-001",
        "BR-OPP-001-R-FILLER-001",
        "BR-OPP-001-R-REPEAT-001",
    ]
    
    evidence_ref = {
        "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
        "text_snippets": ["test"],
    }
    
    for rule_id in rule_ids:
        suggestion = build_template_suggestion(rule_id, evidence_ref)
        
        # Validate structure
        ok, reason = validate_suggestions([suggestion])
        assert ok, f"Rule {rule_id} produced invalid suggestion: {reason}"
        
        # Check drill_id is in allowlist
        drill_id = suggestion["drill"]["drill_id"]
        assert drill_id in DRILL_ID_ALLOWLIST, f"drill_id '{drill_id}' not in allowlist for rule {rule_id}"


def test_fallback_suggestions_empty_triggers() -> None:
    """
    Test fallback with empty triggers returns empty suggestions.
    """
    report = _create_minimal_report(top_trigger_id=None, triggers=[])
    
    suggestions, warnings = build_fallback_suggestions(report, "test_reason")
    
    assert suggestions == [], "Expected empty suggestions for empty triggers"
    assert "NO_TRIGGERS" in warnings, "Expected NO_TRIGGERS warning"


# ========================================
# New护栏 tests (S3.4 fixes)
# ========================================

def test_speed_rule_wpm_high_uses_slow_10_percent() -> None:
    """
    Test SPEED rule with high WPM uses SLOW_10_PERCENT drill.
    """
    triggers = [
        {
            "id": "BR-OPP-001-R-SPEED-001",
            "severity": "P1",
            "impact_score": 0.5,
            "weight": 1.0,
            "priority_score": 0.5,
            "conflict_priority": 1,
            "trigger_count": 1,
            "wpm": 200,  # High WPM
            "evidence": {
                "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                "text_snippets": ["test snippet"],
            },
        }
    ]
    report = _create_minimal_report("BR-OPP-001-R-SPEED-001", triggers)
    
    result = step5_llm_feedback(report)
    
    suggestions = result["llm_feedback"]["suggestions"]
    assert len(suggestions) == 1, f"Expected 1 suggestion, got {len(suggestions)}"
    
    drill_id = suggestions[0]["drill"]["drill_id"]
    assert drill_id == "SLOW_10_PERCENT", f"Expected SLOW_10_PERCENT for high WPM, got {drill_id}"


def test_quality_fallback_does_not_add_llm_unavailable() -> None:
    """
    Test that QUALITY_FALLBACK does not add LLM_UNAVAILABLE warning.
    """
    report = _create_minimal_report("BR-OPP-001-R-TASK-001")
    
    suggestions, warnings = build_fallback_suggestions(report, "QUALITY_FALLBACK:bad_json")
    
    assert len(suggestions) == 1, "Expected 1 suggestion"
    assert "PARTIAL_REPORT" in warnings, "warnings must include PARTIAL_REPORT"
    assert "LLM_UNAVAILABLE" not in warnings, "warnings must NOT include LLM_UNAVAILABLE for quality fallback"


def test_mapping_covers_top5() -> None:
    """
    Test that RULE_TO_DRILL_MAP covers all 5 top rule IDs.
    """
    required_keys = {
        "BR-OPP-001-R-TASK-001",
        "BR-OPP-001-R-STRUCT-001",
        "BR-OPP-001-R-SPEED-001",
        "BR-OPP-001-R-FILLER-001",
        "BR-OPP-001-R-REPEAT-001",
    }
    
    for key in required_keys:
        assert key in RULE_TO_DRILL_MAP, f"Missing mapping for {key}"


def test_trace_written_once_when_no_api_key() -> None:
    """
    Test that trace is written exactly once when no API key.
    """
    # Clear trace file if exists
    trace_file = get_trace_file()
    if trace_file.exists():
        trace_file.unlink()
    
    report = _create_minimal_report("BR-OPP-001-R-TASK-001")
    
    # Call step5 (will fallback due to no API key)
    step5_llm_feedback(report)
    
    # Check trace file has exactly 1 line
    assert trace_file.exists(), "Trace file should exist"
    with open(trace_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1, f"Expected 1 trace line, got {len(lines)}"


def test_unknown_rule_id_forces_one_line_takeaway() -> None:
    """
    Test that unknown rule_id forces drill_id=ONE_LINE_TAKEAWAY.
    """
    # Test get_drill_id directly
    drill_id = get_drill_id("UNKNOWN_RULE_123")
    assert drill_id == "ONE_LINE_TAKEAWAY", f"Expected ONE_LINE_TAKEAWAY for unknown rule, got {drill_id}"
    
    # Test is_known_rule_id
    assert not is_known_rule_id("UNKNOWN_RULE_123"), "is_known_rule_id should return False for unknown rule"


def test_speed_rule_wpm_low_uses_preset_openers() -> None:
    """
    Test SPEED rule with low/normal WPM uses PRESET_OPENERS drill.
    """
    triggers = [
        {
            "id": "BR-OPP-001-R-SPEED-001",
            "severity": "P1",
            "impact_score": 0.5,
            "weight": 1.0,
            "priority_score": 0.5,
            "conflict_priority": 1,
            "trigger_count": 1,
            "wpm": 150,  # Normal WPM
            "evidence": {
                "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                "text_snippets": ["test snippet"],
            },
        }
    ]
    report = _create_minimal_report("BR-OPP-001-R-SPEED-001", triggers)
    
    result = step5_llm_feedback(report)
    
    suggestions = result["llm_feedback"]["suggestions"]
    assert len(suggestions) == 1
    
    drill_id = suggestions[0]["drill"]["drill_id"]
    assert drill_id == "PRESET_OPENERS", f"Expected PRESET_OPENERS for normal WPM, got {drill_id}"


def test_speed_rule_no_wpm_uses_preset_openers() -> None:
    """
    Test SPEED rule with no WPM defaults to PRESET_OPENERS.
    """
    triggers = [
        {
            "id": "BR-OPP-001-R-SPEED-001",
            "severity": "P1",
            "impact_score": 0.5,
            "weight": 1.0,
            "priority_score": 0.5,
            "conflict_priority": 1,
            "trigger_count": 1,
            # No wpm field
            "evidence": {
                "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                "text_snippets": ["test snippet"],
            },
        }
    ]
    report = _create_minimal_report("BR-OPP-001-R-SPEED-001", triggers)
    
    result = step5_llm_feedback(report)
    
    suggestions = result["llm_feedback"]["suggestions"]
    assert len(suggestions) == 1
    
    drill_id = suggestions[0]["drill"]["drill_id"]
    assert drill_id == "PRESET_OPENERS", f"Expected PRESET_OPENERS for missing WPM, got {drill_id}"
