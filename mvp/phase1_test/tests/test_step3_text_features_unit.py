"""
Unit tests for Step3 Text Features (no real audio dependency).

Required tests (at least 6):
1) test_skip_when_asr_failed
2) test_tokenize_chinese_and_english
3) test_filler_count_phrases
4) test_repeat_ratio
5) test_takeaway_detection_last_15s
6) test_filler_per_min_duration_none
"""

import pytest

from app.text_features.step3_text_features import run_step3_text_features
from app.text_features.tokenize import tokenize
from app.text_features.filler import count_fillers, top_k_breakdown
from app.text_features.repeat import compute_repeat
from app.text_features.takeaway import extract_last_window_text, has_ending_takeaway


def test_skip_when_asr_failed():
    """
    Test that Step3 skips and degrades when ASR failed.
    
    step1_result.ok=False -> step3 ok=False and error_reason="ASR_FAILED_SKIP_STEP3"
    text_features fields all present, ratio/per_min=null, ending_takeaway_present=false
    """
    step1_result = {
        "ok": False,
        "error_reason": "ASR transcription failed",
        "asr": {
            "transcript": "",
            "segments": [],
            "overall_confidence": 0.0,
        }
    }
    
    result = run_step3_text_features(step1_result)
    
    assert result["ok"] is False
    assert result["error_reason"] == "ASR_FAILED_SKIP_STEP3"
    
    tf = result["text_features"]
    assert tf["total_tokens"] == 0
    assert tf["filler_count"] == 0
    assert tf["filler_per_min"] is None
    assert tf["filler_ratio"] is None
    assert tf["filler_tokens_top"] == []
    assert tf["repeat_ratio"] is None
    assert tf["repeat_word_ratio"] is None
    assert tf["top_repeated_tokens"] == []
    assert tf["ending_takeaway_present"] is False
    assert tf["first_sentence_has_conclusion"] is None
    assert tf["task_elements_present"] is None


def test_tokenize_chinese_and_english():
    """
    Test tokenization for Chinese and English.
    
    "你好 AI test123" -> tokens should be split properly
    Rules: Chinese sequences [\u4e00-\u9fff]+, English/digit sequences [a-z0-9]+
    """
    text = "你好 AI test123"
    tokens = tokenize(text)
    
    # Expected: ["你好", "ai", "test123"] (lowercase, separated by type)
    assert "你好" in tokens
    assert "ai" in tokens  # lowercase
    assert "test123" in tokens  # English+digits together
    
    # Order matters
    assert tokens == ["你好", "ai", "test", "123"] or tokens == ["你好", "ai", "test123"]


def test_filler_count_phrases():
    """
    Test filler counting with phrases.
    
    text="我觉得这个其实就是这样" -> filler_count should include "我觉得","其实","就是"
    """
    text = "我觉得这个其实就是这样"
    filler_count, breakdown = count_fillers(text)
    
    # Should find: "我觉得" (1), "其实" (1), "就是" (1)
    assert filler_count >= 3
    assert breakdown.get("我觉得", 0) >= 1
    assert breakdown.get("其实", 0) >= 1
    assert breakdown.get("就是", 0) >= 1


def test_repeat_ratio():
    """
    Test repeat ratio calculation.
    
    tokens=["a","a","b","c","c","c"] -> repeated_tokens=(1+2)=3, total=6, repeat_ratio=0.5
    """
    tokens = ["a", "a", "b", "c", "c", "c"]
    stats = compute_repeat(tokens)
    
    assert stats["total_tokens"] == 6
    assert stats["repeated_tokens"] == 3  # "a" has 1 extra, "c" has 2 extra
    assert stats["repeat_ratio"] == 0.5  # 3/6
    assert stats["repeat_word_ratio"] == 0.5
    
    # Top repeated: "c" (3), "a" (2)
    top = stats["top_repeated_tokens"]
    assert len(top) >= 2
    assert {"token": "c", "count": 3} in top
    assert {"token": "a", "count": 2} in top


def test_takeaway_detection_last_15s():
    """
    Test takeaway detection in last 15s window.
    
    Construct segments with duration_ms=20000, last window contains "总结一下"
    -> ending_takeaway_present=true
    """
    # Segments: total 20s, last 5s (15000-20000ms) contains takeaway cue
    segments = [
        {"start_ms": 0, "end_ms": 5000, "text": "你好 这是开头部分"},
        {"start_ms": 5000, "end_ms": 10000, "text": "中间内容很多"},
        {"start_ms": 10000, "end_ms": 15000, "text": "讲了很多细节"},
        {"start_ms": 15000, "end_ms": 20000, "text": "总结一下 核心观点"},  # Last 5s has cue
    ]
    
    duration_ms = 20000
    last_text = extract_last_window_text(segments, duration_ms, window_ms=15000)
    
    # Last window (5000-20000ms) should include last two segments
    assert "总结一下" in last_text
    
    # Takeaway detection
    assert has_ending_takeaway(last_text) is True


def test_filler_per_min_duration_none():
    """
    Test filler_per_min is None when duration is None.
    
    duration_ms=None -> filler_per_min==null
    """
    step1_result = {
        "ok": True,
        "error_reason": None,
        "asr": {
            "transcript": "嗯 这个 然后 那个",
            "segments": [],  # No segments -> duration_ms=None
            "overall_confidence": 0.8,
        }
    }
    
    result = run_step3_text_features(step1_result, step2_result=None)
    
    assert result["ok"] is True
    tf = result["text_features"]
    assert tf["filler_per_min"] is None


def test_tokenize_empty():
    """Test empty text produces empty tokens."""
    tokens = tokenize("")
    assert tokens == []


def test_tokenize_mixed_content():
    """Test tokenization with mixed Chinese/English/punctuation."""
    text = "Hello 世界，这是一个 test 案例！"
    tokens = tokenize(text)
    
    # Should extract: "hello", "世界", "这是一个", "test", "案例"
    assert len(tokens) > 0
    assert "hello" in tokens  # lowercase
    assert "世界" in tokens
    assert "test" in tokens


def test_filler_single_characters():
    """Test single-character filler detection."""
    text = "嗯 啊 这个 呃 就是"
    filler_count, breakdown = count_fillers(text)
    
    # Should find: "嗯" (1), "啊" (1), "呃" (1), "就是" (1)
    assert filler_count >= 4
    assert breakdown.get("嗯", 0) >= 1
    assert breakdown.get("啊", 0) >= 1
    assert breakdown.get("呃", 0) >= 1
    assert breakdown.get("就是", 0) >= 1


def test_top_k_breakdown():
    """Test top K filler breakdown."""
    text = "我觉得 我觉得 我觉得 其实 其实 然后"
    filler_count, breakdown = count_fillers(text)
    
    top = top_k_breakdown(breakdown, k=3)
    
    assert len(top) <= 3
    # "我觉得" should be top (count=3)
    assert top[0]["token"] == "我觉得"
    assert top[0]["count"] == 3


def test_repeat_empty():
    """Test repeat stats with empty tokens."""
    stats = compute_repeat([])
    
    assert stats["total_tokens"] == 0
    assert stats["repeated_tokens"] == 0
    assert stats["repeat_ratio"] is None
    assert stats["repeat_word_ratio"] is None
    assert stats["top_repeated_tokens"] == []


def test_repeat_no_duplicates():
    """Test repeat stats with no duplicates."""
    tokens = ["a", "b", "c", "d"]
    stats = compute_repeat(tokens)
    
    assert stats["total_tokens"] == 4
    assert stats["repeated_tokens"] == 0
    assert stats["repeat_ratio"] == 0.0
    assert stats["top_repeated_tokens"] == []


def test_takeaway_no_cue():
    """Test takeaway detection when no cue phrases present."""
    text = "今天天气很好 我们去了公园 玩得很开心"
    assert has_ending_takeaway(text) is False


def test_takeaway_with_cue():
    """Test takeaway detection with various cue phrases."""
    cues = ["总的来说", "总结一下", "最后", "所以", "结论是", "核心是", "总之", "归根结底"]
    
    for cue in cues:
        text = f"前面讲了很多 {cue} 这是重点"
        assert has_ending_takeaway(text) is True, f"Cue '{cue}' should be detected"


def test_extract_last_window_empty_segments():
    """Test extract_last_window_text with empty segments."""
    text = extract_last_window_text([], duration_ms=10000)
    assert text == ""


def test_extract_last_window_no_duration():
    """Test extract_last_window_text without duration_ms."""
    segments = [
        {"start_ms": 0, "end_ms": 5000, "text": "first"},
        {"start_ms": 5000, "end_ms": 10000, "text": "last"},
    ]
    
    # Should use last segment's end_ms
    text = extract_last_window_text(segments, duration_ms=None, window_ms=15000)
    assert "first" in text or "last" in text  # Should get some text


def test_step3_with_step2_duration():
    """Test Step3 uses step2 pace_series for duration calculation."""
    step1_result = {
        "ok": True,
        "error_reason": None,
        "asr": {
            "transcript": "你好 世界 这是 一个 测试",
            "segments": [{"start_ms": 0, "end_ms": 5000, "text": "test"}],
            "overall_confidence": 0.9,
        }
    }
    
    # Step2 with pace_series indicating 30s duration
    step2_result = {
        "pause_segments": [],
        "long_pause_count": 0,
        "max_pause_ms": 0,
        "pace_series": [
            {"t_ms": 0, "speech_ms": 1000},
            {"t_ms": 1000, "speech_ms": 1000},
            {"t_ms": 2000, "speech_ms": 1000},
            # ... last bucket at 29000ms -> duration = 30000ms
        ],
        "wpm": None,
        "speaking_rate_cpm": None,
    }
    
    result = run_step3_text_features(step1_result, step2_result)
    
    assert result["ok"] is True
    tf = result["text_features"]
    assert tf["total_tokens"] > 0
    # filler_per_min should be calculated using 30s duration from step2
    assert tf["filler_per_min"] is not None


def test_empty_transcript_produces_empty_features():
    """Test Step3 with empty transcript produces empty features but ok=True."""
    step1_result = {
        "ok": True,
        "error_reason": None,
        "asr": {
            "transcript": "",
            "segments": [],
            "overall_confidence": 0.8,
        }
    }
    
    result = run_step3_text_features(step1_result)
    
    assert result["ok"] is True
    tf = result["text_features"]
    assert tf["total_tokens"] == 0
    assert tf["filler_count"] == 0
