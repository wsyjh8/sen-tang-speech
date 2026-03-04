"""
Smoke test for Step1 ASR with local audio file.

Runs only when environment variable ASR_TEST_AUDIO is set.
If env var not present, pytest.skip() to avoid CI failure.

Test assertions:
- ok=True
- segments non-empty
- overall_confidence in 0..1
"""

import os

import pytest

from app.asr.step1_asr import run_step1_asr


def test_step1_asr_local_smoke():
    """
    Smoke test: run ASR on local audio file specified by ASR_TEST_AUDIO env var.
    
    Skipped if ASR_TEST_AUDIO not set.
    """
    audio_path = os.environ.get("ASR_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("ASR_TEST_AUDIO environment variable not set")
    
    # Run ASR
    result = run_step1_asr(audio_path=audio_path, language="zh", model_size="small")
    
    # Assert ok=True
    assert result["ok"] is True, f"ASR failed with error: {result.get('error_reason')}"
    
    # Assert segments non-empty
    asr = result["asr"]
    assert len(asr["segments"]) > 0, "Expected non-empty segments"
    
    # Assert overall_confidence in 0..1
    conf = asr["overall_confidence"]
    assert 0.0 <= conf <= 1.0, f"overall_confidence={conf} not in [0, 1]"
    
    # Assert transcript non-empty
    assert len(asr["transcript"]) > 0, "Expected non-empty transcript"
    
    # Assert segments are monotonically increasing
    segments = asr["segments"]
    for i in range(1, len(segments)):
        assert segments[i]["start_ms"] >= segments[i - 1]["start_ms"], \
            f"Segments not monotonic: segment[{i-1}].start_ms={segments[i-1]['start_ms']} > segment[{i}].start_ms={segments[i]['start_ms']}"
