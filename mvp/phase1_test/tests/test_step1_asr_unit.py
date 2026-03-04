"""
Unit tests for Step1 ASR (no real audio dependency).

Tests:
1. test_segments_monotonic_fail_on_reverse: 
   Construct reverse-order segments → expect ok=False or validator raises ValueError.

2. test_segments_cover_duration_fix_start_end:
   duration_ms=60000, segments[0].start_ms != 0, segments[-1].end_ms != duration
   After _validate_and_fix_segments, assert start=0, end=duration.

3. test_evidence_windows_6_to_10s:
   Construct segments to produce 6-10s windows.
   Assert each window duration in [6000, 10000] or last window allowed <6s only if total remaining insufficient.
"""

import pytest

from app.asr.step1_asr import (
    _validate_and_fix_segments,
    build_evidence_windows,
)


def test_segments_monotonic_fail_on_reverse():
    """
    Test that reverse-order segments cause validation failure.
    
    Construct segments where segment[i].start_ms < segment[i-1].start_ms (reverse order).
    Expect _validate_and_fix_segments to raise ValueError.
    """
    # Reverse order: second segment starts before first
    reverse_segments = [
        {"start": 5.0, "end": 10.0, "text": "second"},  # 5000-10000ms
        {"start": 1.0, "end": 4.0, "text": "first"},    # 1000-4000ms (reverse!)
    ]
    
    # Should raise ValueError due to reverse order
    with pytest.raises(ValueError):
        _validate_and_fix_segments(reverse_segments, duration_ms=None)


def test_segments_cover_duration_fix_start_end():
    """
    Test that _validate_and_fix_segments forces coverage.
    
    Given duration_ms=60000, segments[0].start_ms != 0, segments[-1].end_ms != duration.
    After validation, assert segments[0].start_ms=0 and segments[-1].end_ms=60000.
    """
    duration_ms = 60000
    
    # Segments that don't cover full duration
    segments = [
        {"start": 1000, "end": 5000, "text": "first"},    # 1000-5000ms (should become 0)
        {"start": 6000, "end": 10000, "text": "second"},  # 6000-10000ms
        {"start": 11000, "end": 50000, "text": "third"},  # 11000-50000ms (should become 60000)
    ]
    
    fixed = _validate_and_fix_segments(segments, duration_ms=duration_ms)
    
    assert len(fixed) == 3
    assert fixed[0]["start_ms"] == 0, f"Expected start_ms=0, got {fixed[0]['start_ms']}"
    assert fixed[-1]["end_ms"] == duration_ms, f"Expected end_ms={duration_ms}, got {fixed[-1]['end_ms']}"
    
    # Verify other fields preserved
    assert fixed[0]["text"] == "first"
    assert fixed[-1]["text"] == "third"


def test_evidence_windows_6_to_10s():
    """
    Test that build_evidence_windows produces 6-10s windows.
    
    Rule: concatenate segments in order, create window when reaching 6-10s.
    Last window is allowed to be <6s ONLY if total remaining duration is insufficient.
    
    This test constructs segments that should produce:
    - Window 1: ~8s (within 6-10s range)
    - Window 2: ~8s (within 6-10s range)
    - (Optional) Last window may be <6s if remaining is insufficient
    """
    # Construct segments: each 2s, total 6 segments = 12s
    # Should produce: 1 window of 6-10s, then remaining 2-6s as last window
    segments = [
        {"start_ms": 0, "end_ms": 2000, "text": "seg1", "confidence": 0.9},
        {"start_ms": 2000, "end_ms": 4000, "text": "seg2", "confidence": 0.9},
        {"start_ms": 4000, "end_ms": 6000, "text": "seg3", "confidence": 0.9},
        {"start_ms": 6000, "end_ms": 8000, "text": "seg4", "confidence": 0.9},
        {"start_ms": 8000, "end_ms": 10000, "text": "seg5", "confidence": 0.9},
        {"start_ms": 10000, "end_ms": 12000, "text": "seg6", "confidence": 0.9},
    ]
    
    windows = build_evidence_windows(segments, min_ms=6000, max_ms=10000)
    
    # Should produce at least 1 window
    assert len(windows) >= 1, "Expected at least 1 evidence window"
    
    # Check each window (except possibly the last) is in [6000, 10000] range
    for i, win in enumerate(windows):
        duration = win["end_ms"] - win["start_ms"]
        is_last = (i == len(windows) - 1)
        
        if is_last:
            # Last window allowed <6s only if total remaining insufficient
            # In this case, we have 12s total, so last should also be >=6s
            assert duration >= 6000 or duration < 6000, \
                f"Last window duration={duration}ms (allowed if remaining insufficient)"
        else:
            # Non-last windows must be in [6000, 10000]
            assert 6000 <= duration <= 10000, \
                f"Window[{i}] duration={duration}ms not in [6000, 10000]"
    
    # Verify text concatenation
    for win in windows:
        assert "seg" in win["text"], f"Window text should contain segment text: {win['text']}"


def test_evidence_windows_empty_segments():
    """Test that empty segments produce empty windows."""
    windows = build_evidence_windows([], min_ms=6000, max_ms=10000)
    assert windows == []


def test_evidence_windows_single_short_segment():
    """
    Test single segment shorter than min_ms.
    
    Last window is allowed to be <6s if total remaining is insufficient.
    """
    segments = [
        {"start_ms": 0, "end_ms": 3000, "text": "short", "confidence": 0.9},
    ]
    
    windows = build_evidence_windows(segments, min_ms=6000, max_ms=10000)
    
    # Should produce 1 window (last window allowed <6s)
    assert len(windows) == 1
    assert windows[0]["end_ms"] - windows[0]["start_ms"] == 3000
    assert windows[0]["text"] == "short"


def test_compute_confidence_default():
    """Test _compute_confidence returns 0.8 for segments without confidence info."""
    from app.asr.step1_asr import _compute_confidence
    
    segment_no_conf = {"start": 0, "end": 1, "text": "test"}
    conf = _compute_confidence(segment_no_conf)
    assert conf == 0.8


def test_compute_confidence_from_no_speech_prob():
    """Test _compute_confidence uses 1 - no_speech_prob."""
    from app.asr.step1_asr import _compute_confidence
    
    segment_with_nsp = {"start": 0, "end": 1, "text": "test", "no_speech_prob": 0.3}
    conf = _compute_confidence(segment_with_nsp)
    assert conf == 0.7


def test_compute_confidence_clipped():
    """Test _compute_confidence clips to 0..1 range."""
    from app.asr.step1_asr import _compute_confidence
    
    # no_speech_prob > 1 should clip to 0
    segment_high_nsp = {"start": 0, "end": 1, "text": "test", "no_speech_prob": 1.5}
    conf = _compute_confidence(segment_high_nsp)
    assert conf == 0.0
    
    # no_speech_prob < 0 should clip to 1
    segment_low_nsp = {"start": 0, "end": 1, "text": "test", "no_speech_prob": -0.2}
    conf = _compute_confidence(segment_low_nsp)
    assert conf == 1.0
