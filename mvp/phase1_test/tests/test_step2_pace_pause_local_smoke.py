"""
Smoke test for Step2 Pace/Pause with local audio file.

Runs only when environment variable PACE_TEST_AUDIO is set.
If env var not present, pytest.skip() to avoid CI failure.

Test assertions:
- Output has all required keys
- Types are correct
- pause_segments is a list
- long_pause_count >= 0
- max_pause_ms >= 0
- pace_series is a list
- wpm is float or None
- speaking_rate_cpm is float or None
"""

import os

import pytest

from app.acoustic.step2_pace_pause import run_step2_pace_pause


def test_step2_pace_pause_local_smoke():
    """
    Smoke test: run pace/pause on local audio file specified by PACE_TEST_AUDIO env var.
    
    Skipped if PACE_TEST_AUDIO not set.
    """
    audio_path = os.environ.get("PACE_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("PACE_TEST_AUDIO environment variable not set")
    
    # Run Step2 (without ASR result)
    result = run_step2_pace_pause(audio_path=audio_path, asr_result=None)
    
    # Assert all required keys exist
    required_keys = [
        "pause_segments",
        "long_pause_count",
        "max_pause_ms",
        "pace_series",
        "wpm",
        "speaking_rate_cpm",
    ]
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"
    
    # Assert types
    assert isinstance(result["pause_segments"], list), "pause_segments must be a list"
    assert isinstance(result["long_pause_count"], int), "long_pause_count must be int"
    assert isinstance(result["max_pause_ms"], int), "max_pause_ms must be int"
    assert isinstance(result["pace_series"], list), "pace_series must be a list"
    assert result["wpm"] is None or isinstance(result["wpm"], float), "wpm must be float or None"
    assert result["speaking_rate_cpm"] is None or isinstance(result["speaking_rate_cpm"], float), \
        "speaking_rate_cpm must be float or None"
    
    # Assert value constraints
    assert result["long_pause_count"] >= 0, "long_pause_count must be >= 0"
    assert result["max_pause_ms"] >= 0, "max_pause_ms must be >= 0"
    
    # Assert wpm is None when no ASR result provided
    assert result["wpm"] is None, "wpm should be None when asr_result not provided"
    assert result["speaking_rate_cpm"] is None, "speaking_rate_cpm should be None when asr_result not provided"
    
    # Assert pause_segments structure (if any)
    for seg in result["pause_segments"]:
        assert "start_ms" in seg, "pause_segment missing start_ms"
        assert "end_ms" in seg, "pause_segment missing end_ms"
        assert "duration_ms" in seg, "pause_segment missing duration_ms"
        assert isinstance(seg["start_ms"], int), "start_ms must be int"
        assert isinstance(seg["end_ms"], int), "end_ms must be int"
        assert isinstance(seg["duration_ms"], int), "duration_ms must be int"
        assert seg["duration_ms"] == seg["end_ms"] - seg["start_ms"], \
            "duration_ms must equal end_ms - start_ms"
    
    # Assert pace_series structure (if any)
    for bucket in result["pace_series"]:
        assert "t_ms" in bucket, "pace_series bucket missing t_ms"
        assert "speech_ms" in bucket, "pace_series bucket missing speech_ms"
        assert isinstance(bucket["t_ms"], int), "t_ms must be int"
        assert isinstance(bucket["speech_ms"], int), "speech_ms must be int"


def test_step2_pace_pause_with_asr_result_smoke():
    """
    Smoke test: run pace/pause with ASR result for wpm/cpm calculation.
    
    Skipped if PACE_TEST_AUDIO not set.
    """
    audio_path = os.environ.get("PACE_TEST_AUDIO")
    
    if not audio_path:
        pytest.skip("PACE_TEST_AUDIO environment variable not set")
    
    # Mock ASR result
    mock_asr_result = {
        "asr": {
            "transcript": "你好 世界 这是 一个 测试 音频 文件"
        }
    }
    
    # Run Step2 with ASR result
    result = run_step2_pace_pause(audio_path=audio_path, asr_result=mock_asr_result)
    
    # Assert wpm and cpm are calculated (not None) when ASR result provided
    # Note: wpm/cpm may still be None if transcript is empty
    if mock_asr_result["asr"]["transcript"].strip():
        assert result["wpm"] is not None, "wpm should be calculated when transcript provided"
        assert result["speaking_rate_cpm"] is not None, "cpm should be calculated when transcript provided"
        assert isinstance(result["wpm"], float), "wpm must be float"
        assert isinstance(result["speaking_rate_cpm"], float), "cpm must be float"
