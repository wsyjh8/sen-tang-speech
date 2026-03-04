"""
Unit tests for Step2 Pace/Pause (no real audio dependency).

Tests use mock speech_flags to test logic without webrtcvad.

Required tests:
1) test_long_pause_count_threshold_1200ms:
   Construct a pause=1200ms silence, assert it counts in long_pause_count.

2) test_max_pause_ms:
   Construct multiple pauses, assert max_pause_ms is correct.

3) test_pace_series_bucket_1s:
   Given 10 speech frames in 1s, assert speech_ms == 10 * frame_ms.
"""

import pytest

from app.acoustic.step2_pace_pause import (
    _speech_flags_to_pause_segments,
    _compute_pace_series,
    _compute_wpm,
    _compute_cpm,
)


def test_long_pause_count_threshold_1200ms():
    """
    Test that a pause exactly at 1200ms threshold is counted.
    
    Construct speech_flags with a 1200ms silence (40 frames @ 30ms).
    Assert long_pause_count >= 1.
    """
    frame_ms = 30
    
    # Create flags: 10 speech, 40 silence (1200ms), 10 speech
    # Total: 60 frames
    flags = [True] * 10 + [False] * 40 + [True] * 10
    
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms)
    
    # Should have 1 pause segment
    assert len(pause_segments) == 1
    
    # Duration should be 40 * 30 = 1200ms
    pause = pause_segments[0]
    assert pause["duration_ms"] == 1200
    
    # Count long pauses (>= 1200ms)
    long_pause_count = sum(1 for seg in pause_segments if seg["duration_ms"] >= 1200)
    assert long_pause_count == 1, "Pause of 1200ms should be counted as long pause"


def test_max_pause_ms():
    """
    Test max_pause_ms calculation with multiple pauses.
    
    Construct: 300ms pause, 900ms pause, 1500ms pause.
    Assert max_pause_ms == 1500.
    """
    frame_ms = 30
    
    # Create flags: speech, 10 frames silence (300ms), speech, 30 frames silence (900ms),
    # speech, 50 frames silence (1500ms), speech
    flags = (
        [True] * 10 +
        [False] * 10 +  # 300ms
        [True] * 10 +
        [False] * 30 +  # 900ms
        [True] * 10 +
        [False] * 50 +  # 1500ms
        [True] * 10
    )
    
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms)
    
    # Should have 3 pause segments
    assert len(pause_segments) == 3
    
    # Calculate max_pause_ms
    max_pause_ms = max(seg["duration_ms"] for seg in pause_segments)
    assert max_pause_ms == 1500, f"Expected max_pause_ms=1500, got {max_pause_ms}"
    
    # Verify individual durations
    durations = [seg["duration_ms"] for seg in pause_segments]
    assert 300 in durations
    assert 900 in durations
    assert 1500 in durations


def test_pace_series_bucket_1s():
    """
    Test pace_series bucket calculation.
    
    Given 10 speech frames in 1s (10 * 30ms = 300ms speech in first bucket),
    assert speech_ms for first bucket == 10 * frame_ms.
    """
    frame_ms = 30
    bucket_ms = 1000
    
    # Create 34 frames (34 * 30 = 1020ms, just over 1 bucket)
    # First 10 frames are speech, rest are silence
    flags = [True] * 10 + [False] * 24
    
    pace_series = _compute_pace_series(flags, frame_ms, bucket_ms)
    
    # Should have at least 1 bucket (1020ms / 1000ms = 1 full bucket + partial)
    assert len(pace_series) >= 1
    
    # First bucket (0-1000ms): should contain all 10 speech frames
    # 10 frames * 30ms = 300ms speech
    first_bucket = pace_series[0]
    assert first_bucket["t_ms"] == 0
    assert first_bucket["speech_ms"] == 10 * frame_ms, \
        f"Expected speech_ms={10 * frame_ms}, got {first_bucket['speech_ms']}"


def test_pace_series_multiple_buckets():
    """
    Test pace_series with multiple buckets.
    
    Create 100 frames (3000ms) with alternating speech/silence patterns.
    """
    frame_ms = 30
    bucket_ms = 1000
    
    # 100 frames = 3000ms = 3 buckets
    # Pattern: 10 speech, 10 silence, 10 speech, 10 silence, ...
    flags = []
    for i in range(5):
        flags.extend([True] * 10)  # 10 speech
        flags.extend([False] * 10)  # 10 silence
    
    pace_series = _compute_pace_series(flags, frame_ms, bucket_ms)
    
    # Should have 3 buckets (3000ms / 1000ms)
    assert len(pace_series) == 3
    
    # Each bucket should have t_ms at 0, 1000, 2000
    assert pace_series[0]["t_ms"] == 0
    assert pace_series[1]["t_ms"] == 1000
    assert pace_series[2]["t_ms"] == 2000


def test_speech_flags_to_pause_segments_empty():
    """Test empty flags produce empty pause segments."""
    pause_segments = _speech_flags_to_pause_segments([], frame_ms=30)
    assert pause_segments == []


def test_speech_flags_to_pause_segments_all_speech():
    """Test all speech flags produce no pause segments."""
    flags = [True] * 100
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms=30)
    assert pause_segments == []


def test_speech_flags_to_pause_segments_all_silence():
    """Test all silence flags produce one pause segment covering full duration."""
    flags = [False] * 100
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms=30)
    
    assert len(pause_segments) == 1
    assert pause_segments[0]["start_ms"] == 0
    assert pause_segments[0]["end_ms"] == 100 * 30
    assert pause_segments[0]["duration_ms"] == 100 * 30


def test_compute_wpm_with_transcript():
    """Test wpm calculation with transcript."""
    asr_result = {
        "asr": {
            "transcript": "你好 世界 这是 一个 测试"  # 5 tokens
        }
    }
    audio_duration_ms = 60000  # 1 minute
    
    wpm = _compute_wpm(asr_result, audio_duration_ms)
    
    assert wpm is not None
    assert wpm == 5.0, f"Expected wpm=5.0, got {wpm}"


def test_compute_wpm_no_transcript():
    """Test wpm is None when transcript is empty."""
    asr_result = {
        "asr": {
            "transcript": ""
        }
    }
    audio_duration_ms = 60000
    
    wpm = _compute_wpm(asr_result, audio_duration_ms)
    assert wpm is None


def test_compute_wpm_no_asr_result():
    """Test wpm is None when asr_result is None."""
    wpm = _compute_wpm(None, 60000)
    assert wpm is None


def test_compute_cpm_with_transcript():
    """Test cpm calculation with transcript."""
    asr_result = {
        "asr": {
            "transcript": "你好世界"  # 4 characters
        }
    }
    audio_duration_ms = 60000  # 1 minute
    
    cpm = _compute_cpm(asr_result, audio_duration_ms)
    
    assert cpm is not None
    assert cpm == 4.0, f"Expected cpm=4.0, got {cpm}"


def test_compute_cpm_no_transcript():
    """Test cpm is None when transcript is empty."""
    asr_result = {
        "asr": {
            "transcript": ""
        }
    }
    audio_duration_ms = 60000
    
    cpm = _compute_cpm(asr_result, audio_duration_ms)
    assert cpm is None


def test_pause_at_end_of_audio():
    """Test pause segment that continues to end of audio."""
    frame_ms = 30
    
    # 10 speech frames, then 20 silence frames to end
    flags = [True] * 10 + [False] * 20
    
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms)
    
    assert len(pause_segments) == 1
    assert pause_segments[0]["start_ms"] == 10 * 30
    assert pause_segments[0]["end_ms"] == 30 * 30
    assert pause_segments[0]["duration_ms"] == 20 * 30


def test_pause_shorter_than_threshold():
    """Test that pauses shorter than 1200ms are not counted as long."""
    frame_ms = 30
    
    # Create a 300ms pause (10 frames)
    flags = [True] * 10 + [False] * 10 + [True] * 10
    
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms)
    
    assert len(pause_segments) == 1
    assert pause_segments[0]["duration_ms"] == 300
    
    long_pause_count = sum(1 for seg in pause_segments if seg["duration_ms"] >= 1200)
    assert long_pause_count == 0, "300ms pause should not be counted as long"
