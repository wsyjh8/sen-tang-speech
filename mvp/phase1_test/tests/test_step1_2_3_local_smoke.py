"""
Smoke test for Step1-2-3 pipeline with local audio file.

Runs only when environment variable PIPELINE_TEST_AUDIO is set.
If env var not present, pytest.skip() to avoid CI failure.

Test assertions:
- step1 ok=True
- step2 has all required keys
- step3 has all required keys and total_tokens>=1
"""

import os

import pytest

from app.asr.step1_asr import run_step1_asr
from app.acoustic.step2_pace_pause import run_step2_pace_pause
from app.text_features.step3_text_features import run_step3_text_features


def test_step1_2_3_local_smoke():
    """
    Smoke test: run full Step1-2-3 pipeline on local audio.
    
    Skipped if PIPELINE_TEST_AUDIO not set.
    """
    audio_path = os.environ.get("PIPELINE_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("PIPELINE_TEST_AUDIO environment variable not set")
    
    # ========== Step1: ASR ==========
    step1_result = run_step1_asr(audio_path=audio_path, language="zh", model_size="small")
    
    # Assert Step1 success
    assert step1_result["ok"] is True, f"Step1 failed: {step1_result.get('error_reason')}"
    
    # Assert Step1 output structure
    asr = step1_result.get("asr", {})
    assert "transcript" in asr
    assert "segments" in asr
    assert "overall_confidence" in asr
    
    # Assert transcript non-empty
    assert len(asr["transcript"]) > 0, "Expected non-empty transcript"
    
    # ========== Step2: Pace/Pause ==========
    step2_result = run_step2_pace_pause(
        audio_path=audio_path,
        asr_result=step1_result
    )
    
    # Assert Step2 output structure
    required_step2_keys = [
        "pause_segments",
        "long_pause_count",
        "max_pause_ms",
        "pace_series",
        "wpm",
        "speaking_rate_cpm",
    ]
    for key in required_step2_keys:
        assert key in step2_result, f"Step2 missing key: {key}"
    
    # Assert types
    assert isinstance(step2_result["pause_segments"], list)
    assert isinstance(step2_result["long_pause_count"], int)
    assert isinstance(step2_result["max_pause_ms"], int)
    assert isinstance(step2_result["pace_series"], list)
    
    # ========== Step3: Text Features ==========
    step3_result = run_step3_text_features(
        step1_result=step1_result,
        step2_result=step2_result
    )
    
    # Assert Step3 success (since Step1 succeeded)
    assert step3_result["ok"] is True, f"Step3 failed: {step3_result.get('error_reason')}"
    
    # Assert Step3 output structure
    assert "text_features" in step3_result
    tf = step3_result["text_features"]
    
    required_step3_keys = [
        "total_tokens",
        "filler_count",
        "filler_per_min",
        "filler_ratio",
        "filler_tokens_top",
        "repeat_ratio",
        "repeat_word_ratio",
        "top_repeated_tokens",
        "ending_takeaway_present",
        "first_sentence_has_conclusion",
        "task_elements_present",
    ]
    for key in required_step3_keys:
        assert key in tf, f"Step3 missing key: {key}"
    
    # Assert total_tokens >= 1 (since transcript is non-empty)
    assert tf["total_tokens"] >= 1, f"Expected total_tokens>=1, got {tf['total_tokens']}"
    
    # Assert types
    assert isinstance(tf["total_tokens"], int)
    assert isinstance(tf["filler_count"], int)
    assert isinstance(tf["filler_tokens_top"], list)
    assert isinstance(tf["top_repeated_tokens"], list)
    assert isinstance(tf["ending_takeaway_present"], bool)
    
    # Assert ratios are either float or None
    assert tf["filler_ratio"] is None or isinstance(tf["filler_ratio"], float)
    assert tf["filler_per_min"] is None or isinstance(tf["filler_per_min"], float)
    assert tf["repeat_ratio"] is None or isinstance(tf["repeat_ratio"], float)
    assert tf["repeat_word_ratio"] is None or isinstance(tf["repeat_word_ratio"], float)
