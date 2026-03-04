"""
Smoke test for Step1-5 full pipeline.

Runs only when environment variable PIPELINE_TEST_AUDIO is set.
If env var not present, pytest.skip() to avoid CI failure.

Test assertions:
- report has all required top-level keys
- No forbidden fields (root next_target, rule_id, evidence_refs)
- rule_engine.triggers is list
- llm_feedback.suggestions is list
"""

import os

import pytest

from app.pipeline.full_pipeline import run_step1_to_step5


def _check_no_forbidden_fields(obj, path=""):
    """Recursively check for forbidden fields."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            # Check for forbidden field names
            if key in ("rule_id", "evidence_refs"):
                raise AssertionError(f"Forbidden field '{key}' found at {current_path}")
            # Check for root-level next_target
            if path == "" and key == "next_target":
                raise AssertionError(f"Forbidden root-level field 'next_target' found")
            _check_no_forbidden_fields(value, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_no_forbidden_fields(item, f"{path}[{i}]")


def test_step1_5_demo_smoke():
    """
    Smoke test: run full Step1-5 pipeline on local audio.
    
    Skipped if PIPELINE_TEST_AUDIO not set.
    Uses use_llm=0 to ensure deterministic output.
    """
    audio_path = os.environ.get("PIPELINE_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("PIPELINE_TEST_AUDIO environment variable not set")
    
    # Run full pipeline with LLM forced off (deterministic)
    report = run_step1_to_step5(audio_path, use_llm=False)
    
    # Assert required top-level keys
    required_keys = [
        "pol_version",
        "session",
        "scores",
        "rule_engine",
        "llm_feedback",
        "warnings",
    ]
    for key in required_keys:
        assert key in report, f"Missing required key: {key}"
    
    # Assert no forbidden fields
    _check_no_forbidden_fields(report)
    
    # Assert rule_engine structure
    rule_engine = report["rule_engine"]
    assert "triggers" in rule_engine, "rule_engine missing 'triggers'"
    assert isinstance(rule_engine["triggers"], list), "rule_engine.triggers must be list"
    
    # top_trigger_id should be str or None
    top_trigger_id = rule_engine.get("top_trigger_id")
    assert top_trigger_id is None or isinstance(top_trigger_id, str), \
        "top_trigger_id must be str or None"
    
    # Assert llm_feedback structure
    llm_feedback = report["llm_feedback"]
    assert "suggestions" in llm_feedback, "llm_feedback missing 'suggestions'"
    assert isinstance(llm_feedback["suggestions"], list), \
        "llm_feedback.suggestions must be list"
    
    # Assert session structure
    session = report["session"]
    assert "session_id" in session, "session missing 'session_id'"
    assert "pol_version" in report, "Missing pol_version"
    
    # Assert scores structure
    scores = report["scores"]
    assert "overall" in scores, "scores missing 'overall'"


def test_step1_5_demo_with_llm_smoke():
    """
    Smoke test: run full Step1-5 pipeline with LLM enabled.
    
    Skipped if PIPELINE_TEST_AUDIO not set.
    Note: This test may fail if LLM API is unavailable.
    """
    audio_path = os.environ.get("PIPELINE_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("PIPELINE_TEST_AUDIO environment variable not set")
    
    # Run full pipeline with LLM enabled
    report = run_step1_to_step5(audio_path, use_llm=True)
    
    # Assert required top-level keys
    required_keys = [
        "pol_version",
        "session",
        "scores",
        "rule_engine",
        "llm_feedback",
        "warnings",
    ]
    for key in required_keys:
        assert key in report, f"Missing required key: {key}"
    
    # Assert no forbidden fields
    _check_no_forbidden_fields(report)
    
    # Assert llm_feedback.suggestions is list (may have 0+ suggestions after fallback)
    llm_feedback = report["llm_feedback"]
    assert "suggestions" in llm_feedback, "llm_feedback missing 'suggestions'"
    assert isinstance(llm_feedback["suggestions"], list), \
        "llm_feedback.suggestions must be list"
