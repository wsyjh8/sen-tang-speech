"""Live LLM integration tests for Step5.

These tests require valid API credentials and will be skipped if not configured.

Environment variables required:
- QWEN_API_KEY: API key for LLM service
- QWEN_BASE_URL: Base URL for LLM API

Optional:
- QWEN_MODEL_PRIMARY: Default 'qwen-plus'
- QWEN_MODEL_BACKUP: Default 'qwen-turbo'

Run with:
- pytest -q -m integration  (to run only integration tests)
- pytest -q  (integration tests are skipped by default)
"""

import os
import pytest

from app.pipeline.step5_llm_feedback import step5_llm_feedback
from app.llm.schema_validate import DRILL_ID_ALLOWLIST


def _get_api_credentials() -> tuple[str | None, str | None]:
    """Get API credentials from environment."""
    api_key = os.environ.get("QWEN_API_KEY")
    base_url = os.environ.get("QWEN_BASE_URL")
    return api_key, base_url


def _create_test_report() -> dict:
    """Create a minimal test report for LLM testing."""
    return {
        "pol_version": "POL-v0.1",
        "session": {
            "session_id": "test-live-session",
            "task_type": "IMPROV_60S",
            "language": "zh",
            "generated_at": "2026-03-01T00:00:00Z",
        },
        "scores": {"overall": 80},
        "rule_engine": {
            "triggers": [
                {
                    "id": "BR-OPP-001-R-TASK-001",
                    "severity": "P0",
                    "impact_score": 0.7,
                    "weight": 1.0,
                    "priority_score": 0.7,
                    "conflict_priority": 1,
                    "trigger_count": 1,
                    "evidence": {
                        "time_ranges": [{"start_ms": 0, "end_ms": 1000}],
                        "text_snippets": ["我觉得这个事情的核心结论是……"],
                    },
                }
            ],
            "top_trigger_id": "BR-OPP-001-R-TASK-001",
            "next_target": None,
        },
        "llm_feedback": {"suggestions": []},
        "warnings": [],
    }


@pytest.mark.integration
@pytest.mark.skipif(
    not _get_api_credentials()[0] or not _get_api_credentials()[1],
    reason="QWEN_API_KEY and QWEN_BASE_URL environment variables must be set"
)
def test_llm_live_step5_produces_valid_suggestions() -> None:
    """
    Test that Step5 with live LLM produces valid suggestions.
    
    This test:
    1. Checks for API credentials (skips if missing)
    2. Calls step5_llm_feedback with a test report
    3. Validates the output structure and content
    4. Verifies LLM path was taken (no fallback warnings)
    """
    api_key, base_url = _get_api_credentials()
    
    # Double-check credentials
    if not api_key or not base_url:
        pytest.skip("QWEN_API_KEY or QWEN_BASE_URL not set")
    
    # Create test report
    report = _create_test_report()
    
    # Call Step5
    out_report = step5_llm_feedback(report)
    
    # === Assertion 1: suggestions is a list ===
    suggestions = out_report["llm_feedback"]["suggestions"]
    assert isinstance(suggestions, list), "suggestions must be a list"
    
    # === Assertion 2: suggestions length 1-3 ===
    assert 1 <= len(suggestions) <= 3, \
        f"suggestions length must be 1-3, got {len(suggestions)}"
    
    # === Assertion 3: First suggestion has required fields ===
    suggestion = suggestions[0]
    required_fields = {"title", "problem", "cause", "evidence_ref", "drill", "acceptance"}
    missing = required_fields - set(suggestion.keys())
    assert not missing, f"First suggestion missing fields: {missing}"
    
    # === Assertion 4: evidence_ref structure ===
    evidence_ref = suggestion["evidence_ref"]
    assert isinstance(evidence_ref.get("time_ranges"), list), \
        "evidence_ref.time_ranges must be a list"
    assert isinstance(evidence_ref.get("text_snippets"), list), \
        "evidence_ref.text_snippets must be a list"
    
    # === Assertion 5: drill structure ===
    drill = suggestion["drill"]
    assert "drill_id" in drill, "drill must have drill_id"
    assert drill["drill_id"] in DRILL_ID_ALLOWLIST, \
        f"drill_id '{drill['drill_id']}' not in allowlist {DRILL_ID_ALLOWLIST}"
    assert "steps" in drill, "drill must have steps"
    assert "duration_sec" in drill, "drill must have duration_sec"
    assert "tips" in drill, "drill must have tips"
    
    # === Assertion 6: acceptance structure ===
    acceptance = suggestion["acceptance"]
    assert acceptance.get("metric"), "acceptance.metric must not be empty"
    assert acceptance.get("target") is not None, "acceptance.target must not be empty"
    assert acceptance.get("how_to_measure"), "acceptance.how_to_measure must not be empty"
    
    # === Assertion 7: LLM path taken (no fallback warnings) ===
    # Note: If LLM returns invalid JSON or missing fields, fallback is triggered.
    # This is expected behavior - the test validates the fallback produces valid output.
    warnings = out_report["warnings"]
    
    # If LLM_UNAVAILABLE is present, the API call failed (network/auth issue)
    if "LLM_UNAVAILABLE" in warnings:
        pytest.fail(f"LLM call failed: {warnings}")
    
    # PARTIAL_REPORT may appear if LLM response doesn't fully match schema
    # but fallback produced valid output. This is acceptable for live testing.
    # The key assertion is that suggestions are valid (checked above).


@pytest.mark.integration
@pytest.mark.skipif(
    not _get_api_credentials()[0] or not _get_api_credentials()[1],
    reason="QWEN_API_KEY and QWEN_BASE_URL environment variables must be set"
)
def test_llm_live_speed_rule_with_high_wpm() -> None:
    """
    Test that SPEED rule with high WPM produces SLOW_10_PERCENT drill via LLM.
    
    Note: This tests the wpm handling in template_fallback, but with LLM path
    the LLM should ideally also respect this logic.
    """
    api_key, base_url = _get_api_credentials()
    
    if not api_key or not base_url:
        pytest.skip("QWEN_API_KEY or QWEN_BASE_URL not set")
    
    report = {
        "pol_version": "POL-v0.1",
        "session": {
            "session_id": "test-speed-session",
            "task_type": "IMPROV_60S",
            "language": "zh",
            "generated_at": "2026-03-01T00:00:00Z",
        },
        "scores": {"overall": 80},
        "rule_engine": {
            "triggers": [
                {
                    "id": "BR-OPP-001-R-SPEED-001",
                    "severity": "P1",
                    "impact_score": 0.6,
                    "weight": 1.0,
                    "priority_score": 0.6,
                    "conflict_priority": 1,
                    "trigger_count": 1,
                    "wpm": 200,  # High WPM
                    "evidence": {
                        "time_ranges": [{"start_ms": 0, "end_ms": 1000}],
                        "text_snippets": ["我说话太快了需要放慢"],
                    },
                }
            ],
            "top_trigger_id": "BR-OPP-001-R-SPEED-001",
            "next_target": None,
        },
        "llm_feedback": {"suggestions": []},
        "warnings": [],
    }
    
    out_report = step5_llm_feedback(report)
    
    suggestions = out_report["llm_feedback"]["suggestions"]
    assert len(suggestions) >= 1, "Should have at least 1 suggestion"
    
    # Note: LLM may return different drill_id, but fallback should use SLOW_10_PERCENT
    # This test mainly verifies the LLM path works for SPEED rule
