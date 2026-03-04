"""
Takeaway (ending conclusion) detection for Step3 Text Features (MVP-0).

Rules:
- Extract text from last 10-15s window (from segments)
- Check for cue phrases: ["总的来说","总结一下","最后","所以","结论是","核心是","总之","归根结底"]
- ending_takeaway_present = any(cue in last_text)

first_sentence_has_conclusion and task_elements_present return None in MVP (not implemented).
"""

from typing import List, Dict, Any, Optional

# Cue phrases for takeaway detection (frozen MVP list)
TAKEAWAY_CUES = [
    "总的来说",
    "总结一下",
    "最后",
    "所以",
    "结论是",
    "核心是",
    "总之",
    "归根结底",
]

# Default window size for ending detection (ms)
DEFAULT_WINDOW_MS = 15000


def extract_last_window_text(
    segments: List[Dict[str, Any]],
    duration_ms: Optional[int],
    window_ms: int = DEFAULT_WINDOW_MS
) -> str:
    """
    Extract text from the last window of audio.
    
    Args:
        segments: ASR segments list (each has start_ms, end_ms, text)
        duration_ms: audio duration in ms (or None)
        window_ms: window size in ms (default 15000)
    
    Returns:
        concatenated text from segments falling in [duration_ms - window_ms, duration_ms]
    """
    if not segments:
        return ""
    
    # Determine duration_ms if not provided
    if duration_ms is None:
        # Use last segment end_ms
        duration_ms = segments[-1].get("end_ms", 0)
    
    if duration_ms is None or duration_ms <= 0:
        return ""
    
    # Calculate window start
    window_start = max(0, duration_ms - window_ms)
    
    # Collect text from segments overlapping with window
    texts = []
    for seg in segments:
        seg_start = seg.get("start_ms", 0)
        seg_end = seg.get("end_ms", 0)
        
        # Check if segment overlaps with window
        if seg_end > window_start:
            texts.append(seg.get("text", ""))
    
    return "".join(texts)


def has_ending_takeaway(text: str) -> bool:
    """
    Check if text contains takeaway cue phrases.
    
    Args:
        text: text to check
    
    Returns:
        True if any cue phrase found
    """
    for cue in TAKEAWAY_CUES:
        if cue in text:
            return True
    return False


def first_sentence_has_conclusion(text: str) -> Optional[bool]:
    """
    Check if first sentence has conclusion markers.
    
    MVP: Returns None (not implemented).
    
    Args:
        text: full transcript text
    
    Returns:
        None in MVP
    """
    return None


def task_elements_present(text: str) -> Optional[Dict[str, Any]]:
    """
    Check for task-specific elements.
    
    MVP: Returns None (not implemented).
    
    Args:
        text: full transcript text
    
    Returns:
        None in MVP
    """
    return None
