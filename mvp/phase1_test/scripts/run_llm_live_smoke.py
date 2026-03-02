#!/usr/bin/env python3
"""Live LLM smoke test for Step5.

This script manually tests the LLM integration by calling step5_llm_feedback
with a test report and verifying the output.

Environment variables required:
- QWEN_API_KEY: API key for LLM service
- QWEN_BASE_URL: Base URL for LLM API

Optional:
- QWEN_MODEL_PRIMARY: Default 'qwen-plus'
- QWEN_MODEL_BACKUP: Default 'qwen-turbo'

Usage:
    python scripts/run_llm_live_smoke.py

Exit codes:
- 0: Success (LLM path taken, valid output)
- 1: Failure (missing env vars, invalid output, or fallback triggered)
"""

import os
import sys

from app.pipeline.step5_llm_feedback import step5_llm_feedback
from app.llm.schema_validate import DRILL_ID_ALLOWLIST


def _check_env_vars() -> bool:
    """Check if required environment variables are set."""
    api_key = os.environ.get("QWEN_API_KEY")
    base_url = os.environ.get("QWEN_BASE_URL")
    
    if not api_key:
        print("ERROR: QWEN_API_KEY environment variable not set")
        return False
    
    if not base_url:
        print("ERROR: QWEN_BASE_URL environment variable not set")
        return False
    
    return True


def _create_test_report() -> dict:
    """Create a minimal test report for LLM testing."""
    return {
        "pol_version": "POL-v0.1",
        "session": {
            "session_id": "smoke-test-session",
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


def main() -> int:
    """Run the smoke test."""
    print("=" * 60)
    print("Step5 LLM Live Smoke Test")
    print("=" * 60)
    
    # Check environment variables
    if not _check_env_vars():
        print("\nSkipping test: environment variables not configured")
        print("Set QWEN_API_KEY and QWEN_BASE_URL to run this test")
        return 1
    
    print(f"\nEnvironment:")
    print(f"  QWEN_API_KEY: {'***' + os.environ.get('QWEN_API_KEY', '')[-4:]}")
    print(f"  QWEN_BASE_URL: {os.environ.get('QWEN_BASE_URL')}")
    print(f"  QWEN_MODEL_PRIMARY: {os.environ.get('QWEN_MODEL_PRIMARY', 'qwen-plus')}")
    print(f"  QWEN_MODEL_BACKUP: {os.environ.get('QWEN_MODEL_BACKUP', 'qwen-turbo')}")
    
    # Create test report
    print("\nCreating test report...")
    report = _create_test_report()
    
    # Call Step5
    print("Calling step5_llm_feedback...")
    try:
        out_report = step5_llm_feedback(report)
    except Exception as e:
        print(f"ERROR: step5_llm_feedback raised exception: {e}")
        return 1
    
    # Validate output
    print("\nValidating output...")
    
    suggestions = out_report["llm_feedback"]["suggestions"]
    warnings = out_report["warnings"]
    
    # Check suggestions is a list
    if not isinstance(suggestions, list):
        print(f"FAIL: suggestions is not a list: {type(suggestions)}")
        return 1
    
    # Check suggestions length
    if not (1 <= len(suggestions) <= 3):
        print(f"FAIL: suggestions length not in 1-3: {len(suggestions)}")
        return 1
    
    print(f"  Suggestions count: {len(suggestions)}")
    
    # Check first suggestion structure
    suggestion = suggestions[0]
    required_fields = {"title", "problem", "cause", "evidence_ref", "drill", "acceptance"}
    missing = required_fields - set(suggestion.keys())
    if missing:
        print(f"FAIL: First suggestion missing fields: {missing}")
        return 1
    
    # Check drill_id
    drill_id = suggestion["drill"]["drill_id"]
    if drill_id not in DRILL_ID_ALLOWLIST:
        print(f"FAIL: drill_id '{drill_id}' not in allowlist")
        return 1
    
    print(f"  First suggestion drill_id: {drill_id}")
    
    # Check acceptance
    acceptance = suggestion["acceptance"]
    if not acceptance.get("metric"):
        print("FAIL: acceptance.metric is empty")
        return 1
    if acceptance.get("target") is None:
        print("FAIL: acceptance.target is empty")
        return 1
    if not acceptance.get("how_to_measure"):
        print("FAIL: acceptance.how_to_measure is empty")
        return 1
    
    # Check warnings (LLM path should not have fallback warnings)
    print(f"  Warnings: {warnings}")
    
    if "LLM_UNAVAILABLE" in warnings:
        print("FAIL: LLM_UNAVAILABLE in warnings (LLM call failed)")
        return 1
    
    if "PARTIAL_REPORT" in warnings:
        print("FAIL: PARTIAL_REPORT in warnings (output is fallback)")
        return 1
    
    # Success
    print("\n" + "=" * 60)
    print("SUCCESS: LLM path taken, output is valid")
    print("=" * 60)
    
    # Print first suggestion summary
    print("\nFirst suggestion summary:")
    print(f"  Title: {suggestion['title'][:50]}...")
    print(f"  Problem: {suggestion['problem'][:50]}...")
    print(f"  Drill: {drill_id}")
    print(f"  Acceptance metric: {acceptance['metric']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
