"""
Step3 Text Features Job (MVP-0).

Input:
- step1_result: dict from Step1 ASR
- step2_result: dict|None from Step2 Pace/Pause (optional, for duration/wpm)

Output:
{
  "ok": bool,
  "error_reason": str|None,
  "text_features": {
    "total_tokens": int,
    "filler_count": int,
    "filler_per_min": float|null,
    "filler_ratio": float|null,
    "filler_tokens_top": [{"token": str, "count": int}],
    "repeat_ratio": float|null,
    "repeat_word_ratio": float|null,
    "top_repeated_tokens": [{"token": str, "count": int}],
    "ending_takeaway_present": bool,
    "first_sentence_has_conclusion": bool|null,
    "task_elements_present": dict|null
  }
}

Hard constraints:
1) If step1_result["ok"] is False -> skip and degrade: output empty artifact with ok=False
2) Tokenization uses frozen regex rules
3) Takeaway detection only looks at last 10-15s text from segments
4) No external heavy dependencies (stdlib only by default)
"""

from typing import Dict, Any, Optional, List

from app.text_features.tokenize import tokenize
from app.text_features.filler import count_fillers, top_k_breakdown
from app.text_features.repeat import compute_repeat
from app.text_features.takeaway import (
    extract_last_window_text,
    has_ending_takeaway,
    first_sentence_has_conclusion,
    task_elements_present,
)


def _compute_duration_ms(step1_result: Dict, step2_result: Optional[Dict]) -> Optional[int]:
    """
    Compute duration_ms with priority:
    1) If step2_result has pace_series: duration_ms = last_bucket.t_ms + 1000
    2) Else use step1_result.asr.segments[-1].end_ms
    3) Else None
    
    Args:
        step1_result: Step1 ASR result
        step2_result: Step2 Pace/Pause result (optional)
    
    Returns:
        duration_ms or None
    """
    # Priority 1: step2 pace_series
    if step2_result is not None:
        pace_series = step2_result.get("pace_series", [])
        if pace_series:
            last_bucket = pace_series[-1]
            return last_bucket.get("t_ms", 0) + 1000
    
    # Priority 2: step1 segments
    asr = step1_result.get("asr", {})
    segments = asr.get("segments", [])
    if segments:
        return segments[-1].get("end_ms")
    
    # Priority 3: None
    return None


def _make_empty_text_features() -> Dict[str, Any]:
    """
    Create an empty text_features artifact for degraded output.
    
    All fields present, ratios/per_min are null, counts are 0.
    """
    return {
        "total_tokens": 0,
        "filler_count": 0,
        "filler_per_min": None,
        "filler_ratio": None,
        "filler_tokens_top": [],
        "repeat_ratio": None,
        "repeat_word_ratio": None,
        "top_repeated_tokens": [],
        "ending_takeaway_present": False,
        "first_sentence_has_conclusion": None,
        "task_elements_present": None,
    }


def run_step3_text_features(
    step1_result: Dict[str, Any],
    step2_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run Step3 Text Features analysis.
    
    Args:
        step1_result: Step1 ASR result dict
        step2_result: Step2 Pace/Pause result dict (optional)
    
    Returns:
        {
          "ok": bool,
          "error_reason": str|None,
          "text_features": {...}
        }
    """
    # Check if Step1 failed
    if not step1_result.get("ok", False):
        return {
            "ok": False,
            "error_reason": "ASR_FAILED_SKIP_STEP3",
            "text_features": _make_empty_text_features(),
        }
    
    # Extract transcript
    asr = step1_result.get("asr", {})
    transcript = asr.get("transcript", "")
    segments = asr.get("segments", [])
    
    if not transcript:
        # Empty transcript -> empty features but ok=True
        return {
            "ok": True,
            "error_reason": None,
            "text_features": _make_empty_text_features(),
        }
    
    # Calculate duration_ms
    duration_ms = _compute_duration_ms(step1_result, step2_result)
    duration_min = (duration_ms / 60000.0) if duration_ms is not None and duration_ms > 0 else None
    
    # Tokenize
    tokens = tokenize(transcript)
    total_tokens = len(tokens)
    
    # Filler count
    filler_count, filler_breakdown = count_fillers(transcript)
    filler_tokens_top = top_k_breakdown(filler_breakdown, k=5)
    
    # Filler ratio and per_min
    filler_ratio = (filler_count / total_tokens) if total_tokens > 0 else None
    filler_per_min = (filler_count / duration_min) if duration_min is not None and duration_min > 0 else None
    
    # Repeat statistics
    repeat_stats = compute_repeat(tokens)
    
    # Takeaway detection (last 15s window)
    last_text = extract_last_window_text(segments, duration_ms, window_ms=15000)
    ending_takeaway_present = has_ending_takeaway(last_text)
    
    # First sentence conclusion (MVP: None)
    first_conclusion = first_sentence_has_conclusion(transcript)
    
    # Task elements (MVP: None)
    task_elements = task_elements_present(transcript)
    
    # Assemble text_features
    text_features = {
        "total_tokens": total_tokens,
        "filler_count": filler_count,
        "filler_per_min": round(filler_per_min, 2) if filler_per_min is not None else None,
        "filler_ratio": round(filler_ratio, 4) if filler_ratio is not None else None,
        "filler_tokens_top": filler_tokens_top,
        "repeat_ratio": repeat_stats.get("repeat_ratio"),
        "repeat_word_ratio": repeat_stats.get("repeat_word_ratio"),
        "top_repeated_tokens": repeat_stats.get("top_repeated_tokens", []),
        "ending_takeaway_present": ending_takeaway_present,
        "first_sentence_has_conclusion": first_conclusion,
        "task_elements_present": task_elements,
    }
    
    return {
        "ok": True,
        "error_reason": None,
        "text_features": text_features,
    }
