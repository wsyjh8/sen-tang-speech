"""
Top5 Rule Evaluator (MVP-0).

Evaluates Step1-3 artifacts and generates triggered_triggers for Top5 rules:
1. TASK (BR-OPP-001-R-TASK-001)
2. STRUCT (BR-OPP-001-R-STRUCT-001)
3. SPEED (BR-OPP-001-R-SPEED-001)
4. FILLER (BR-OPP-001-R-FILLER-001)
5. REPEAT (BR-OPP-001-R-REPEAT-001)

Returns triggered_triggers list with fields required by rank_triggers:
- id: BR rule id
- severity: "P0"|"P1"|"P2"
- impact_score: 0..1
- conflict_priority: int (1 is highest)
- trigger_count: int
- evidence: {"time_ranges": [...], "text_snippets": [...]}
"""

from typing import List, Dict, Any, Optional


def _extract_last_window_text(segments: List[Dict], duration_ms: Optional[int], window_ms: int = 15000) -> str:
    """Extract text from last window of segments."""
    if not segments:
        return ""
    
    if duration_ms is None:
        duration_ms = segments[-1].get("end_ms", 0)
    
    if duration_ms <= 0:
        return ""
    
    window_start = max(0, duration_ms - window_ms)
    texts = []
    for seg in segments:
        seg_end = seg.get("end_ms", 0)
        if seg_end > window_start:
            texts.append(seg.get("text", ""))
    
    return "".join(texts)


def _extract_first_segment_text(segments: List[Dict]) -> str:
    """Extract text from first segment."""
    if not segments:
        return ""
    return segments[0].get("text", "")


def _extract_transcript_snippet(transcript: str, max_chars: int = 200) -> str:
    """Extract snippet from transcript."""
    if not transcript:
        return ""
    if len(transcript) <= max_chars:
        return transcript
    return transcript[:max_chars]


def evaluate_top5(
    step1_result: Dict[str, Any],
    step2_result: Dict[str, Any],
    step3_result: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate Top5 rules from Step1-3 artifacts.
    
    Args:
        step1_result: Step1 ASR result
        step2_result: Step2 Pace/Pause result
        step3_result: Step3 Text Features result
    
    Returns:
        List of triggered_triggers (may be empty if no rules triggered)
    """
    triggered = []
    
    # Extract data from results
    asr = step1_result.get("asr", {})
    transcript = asr.get("transcript", "")
    segments = asr.get("segments", [])
    
    text_features = step3_result.get("text_features", {})
    ending_takeaway = text_features.get("ending_takeaway_present", True)
    first_sentence_conclusion = text_features.get("first_sentence_has_conclusion")
    filler_ratio = text_features.get("filler_ratio")
    repeat_ratio = text_features.get("repeat_ratio")
    
    wpm = step2_result.get("wpm")
    long_pause_count = step2_result.get("long_pause_count", 0)
    max_pause_ms = step2_result.get("max_pause_ms", 0)
    
    # Calculate duration_ms from step2 pace_series or step1 segments
    duration_ms = None
    pace_series = step2_result.get("pace_series", [])
    if pace_series:
        duration_ms = pace_series[-1].get("t_ms", 0) + 1000
    elif segments:
        duration_ms = segments[-1].get("end_ms")
    
    # ========== 1. TASK (BR-OPP-001-R-TASK-001) ==========
    # Trigger if ending_takeaway_present == False
    if ending_takeaway is False:
        last_text = _extract_last_window_text(segments, duration_ms, window_ms=15000)
        snippet = _extract_transcript_snippet(last_text if last_text else transcript)
        
        triggered.append({
            "id": "BR-OPP-001-R-TASK-001",
            "severity": "P1",
            "impact_score": 0.6,
            "conflict_priority": 2,
            "trigger_count": 1,
            "evidence": {
                "time_ranges": [{"start_ms": max(0, (duration_ms or 0) - 15000), "end_ms": duration_ms or 0}] if duration_ms else [],
                "text_snippets": [snippet] if snippet else [],
            },
        })
    
    # ========== 2. STRUCT (BR-OPP-001-R-STRUCT-001) ==========
    # Trigger if first_sentence_has_conclusion is False or None
    if first_sentence_conclusion is False or first_sentence_conclusion is None:
        first_text = _extract_first_segment_text(segments)
        snippet = _extract_transcript_snippet(first_text if first_text else transcript)
        
        triggered.append({
            "id": "BR-OPP-001-R-STRUCT-001",
            "severity": "P2",
            "impact_score": 0.5,
            "conflict_priority": 3,
            "trigger_count": 1,
            "evidence": {
                "time_ranges": [{"start_ms": 0, "end_ms": segments[0].get("end_ms", 5000)}] if segments else [],
                "text_snippets": [snippet] if snippet else [],
            },
        })
    
    # ========== 3. SPEED (BR-OPP-001-R-SPEED-001) ==========
    # Only trigger if wpm is not None
    if wpm is not None:
        # Trigger if wpm > 190 OR wpm < 120
        if wpm > 190 or wpm < 120:
            # impact_score: min(1.0, abs(wpm-160)/80)
            impact_score = min(1.0, abs(wpm - 160) / 80)
            
            # severity: wpm > 220 -> "P0" else "P1"
            severity = "P0" if wpm > 220 else "P1"
            
            snippet = _extract_transcript_snippet(transcript)
            
            triggered.append({
                "id": "BR-OPP-001-R-SPEED-001",
                "severity": severity,
                "impact_score": round(impact_score, 4),
                "conflict_priority": 4,
                "trigger_count": 1,
                "evidence": {
                    "time_ranges": [{"start_ms": 0, "end_ms": duration_ms or 0}] if duration_ms else [],
                    "text_snippets": [snippet] if snippet else [],
                },
            })
    
    # ========== 4. FILLER (BR-OPP-001-R-FILLER-001) ==========
    # Trigger if filler_ratio > 0.03
    if filler_ratio is not None and filler_ratio > 0.03:
        # impact_score: min(1.0, (filler_ratio - 0.03) / 0.10)
        impact_score = min(1.0, (filler_ratio - 0.03) / 0.10)
        
        # severity: filler_ratio > 0.10 -> "P0" else "P1"
        severity = "P0" if filler_ratio > 0.10 else "P1"
        
        snippet = _extract_transcript_snippet(transcript)
        
        triggered.append({
            "id": "BR-OPP-001-R-FILLER-001",
            "severity": severity,
            "impact_score": round(impact_score, 4),
            "conflict_priority": 1,
            "trigger_count": 1,
            "evidence": {
                "time_ranges": [{"start_ms": 0, "end_ms": duration_ms or 0}] if duration_ms else [],
                "text_snippets": [snippet] if snippet else [],
            },
        })
    
    # ========== 5. REPEAT (BR-OPP-001-R-REPEAT-001) ==========
    # Trigger if repeat_ratio > 0.05
    if repeat_ratio is not None and repeat_ratio > 0.05:
        # impact_score: min(1.0, (repeat_ratio - 0.05) / 0.15)
        impact_score = min(1.0, (repeat_ratio - 0.05) / 0.15)
        
        # severity: repeat_ratio > 0.15 -> "P0" else "P1"
        severity = "P0" if repeat_ratio > 0.15 else "P1"
        
        snippet = _extract_transcript_snippet(transcript)
        
        triggered.append({
            "id": "BR-OPP-001-R-REPEAT-001",
            "severity": severity,
            "impact_score": round(impact_score, 4),
            "conflict_priority": 5,
            "trigger_count": 1,
            "evidence": {
                "time_ranges": [{"start_ms": 0, "end_ms": duration_ms or 0}] if duration_ms else [],
                "text_snippets": [snippet] if snippet else [],
            },
        })
    
    return triggered
