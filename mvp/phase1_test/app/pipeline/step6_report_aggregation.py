"""
Step6 Report Aggregation - Final Report Assembly.

Aggregates Step1-5 results into final ReportResponse with:
- scores.overall (deterministic 0-100)
- report_view (chart_data + highlights)
- warnings merge

Single-writer contract:
- scores.overall ONLY written by Step6 (Step4/Step5 must NOT write scores)
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


# Severity penalty for overall score calculation
SEVERITY_PENALTY = {"P0": 30, "P1": 15, "P2": 8}


def _compute_overall_score(triggers: List[dict]) -> int:
    """
    Compute overall score (0-100) deterministically.

    Algorithm:
    - base = 90
    - If triggers non-empty: apply severity penalty from most severe trigger
    - Extra penalty: max(0, len(triggers)-1) * 3
    - overall = clamp(base - severity_penalty - extra, 0, 100)

    Args:
        triggers: List of triggers from rule_engine

    Returns:
        overall score in range 0-100
    """
    base = 90

    if not triggers:
        return base

    # Get most severe penalty (first trigger is highest priority after sorting)
    top_trigger = triggers[0]
    severity = top_trigger.get("severity", "P2")
    severity_penalty = SEVERITY_PENALTY.get(severity, 0)

    # Extra penalty for multiple triggers
    extra_penalty = max(0, len(triggers) - 1) * 3

    # Compute and clamp
    overall = base - severity_penalty - extra_penalty
    return max(0, min(100, overall))


def _build_pace_series(step2_result: Optional[Dict]) -> List[dict]:
    """
    Build pace_series for chart_data from Step2.

    Args:
        step2_result: Step2 pace/pause result

    Returns:
        pace_series list (empty if Step2 unavailable)
    """
    if step2_result is None:
        return []

    pace_series = step2_result.get("pace_series", [])
    if pace_series is None:
        return []

    # Ensure structure: [{ "t_ms": int, "speech_ms": int }]
    return [
        {"t_ms": bucket.get("t_ms", 0), "speech_ms": bucket.get("speech_ms", 0)}
        for bucket in pace_series
    ]


def _build_pause_series(step2_result: Optional[Dict]) -> List[dict]:
    """
    Build pause_series for chart_data from Step2.

    Args:
        step2_result: Step2 pace/pause result

    Returns:
        pause_series list (empty if Step2 unavailable)
    """
    if step2_result is None:
        return []

    pause_segments = step2_result.get("pause_segments", [])
    if pause_segments is None:
        return []

    # Ensure structure: [{ "start_ms": int, "end_ms": int, "duration_ms": int }]
    return [
        {
            "start_ms": seg.get("start_ms", 0),
            "end_ms": seg.get("end_ms", 0),
            "duration_ms": seg.get("duration_ms", 0),
        }
        for seg in pause_segments
    ]


def _find_overlap_text(
    start_ms: int,
    end_ms: int,
    segments: List[dict]
) -> str:
    """
    Find text from segments that overlap with [start_ms, end_ms].

    Args:
        start_ms: highlight start
        end_ms: highlight end
        segments: ASR segments

    Returns:
        Overlapping text or empty string
    """
    if not segments:
        return ""

    texts = []
    for seg in segments:
        seg_start = seg.get("start_ms", 0)
        seg_end = seg.get("end_ms", 0)

        # Check overlap
        if seg_start < end_ms and seg_end > start_ms:
            texts.append(seg.get("text", ""))

    return "".join(texts)


def _build_highlights(
    rule_engine: dict,
    step1_result: Optional[Dict]
) -> List[dict]:
    """
    Build highlights from rule_engine triggers.

    Strategy:
    - Source: rule_engine.triggers[].evidence.time_ranges[]
    - text_snippet: priority = trigger's text_snippets[0] > overlap from segments > ""
    - type: "RULE_EVIDENCE"
    - Sort: (start_ms ASC, end_ms ASC, type ASC, text_snippet ASC)

    Args:
        rule_engine: rule_engine dict from Step4
        step1_result: Step1 ASR result (for segment text lookup)

    Returns:
        highlights list sorted by (start_ms, end_ms, type, text_snippet)
    """
    highlights = []

    triggers = rule_engine.get("triggers", [])
    segments = []
    if step1_result is not None:
        asr = step1_result.get("asr", {})
        segments = asr.get("segments", [])

    for trigger in triggers:
        evidence = trigger.get("evidence", {})
        time_ranges = evidence.get("time_ranges", [])
        text_snippets = evidence.get("text_snippets", [])

        # Get primary snippet (first one)
        primary_snippet = text_snippets[0] if text_snippets else ""

        for time_range in time_ranges:
            start_ms = time_range.get("start_ms", 0)
            end_ms = time_range.get("end_ms", 0)

            # Determine text_snippet
            text_snippet = primary_snippet
            if not text_snippet:
                # Fallback: find overlap from segments
                text_snippet = _find_overlap_text(start_ms, end_ms, segments)

            highlights.append({
                "start_ms": start_ms,
                "end_ms": end_ms,
                "type": "RULE_EVIDENCE",
                "text_snippet": text_snippet,
            })

    # Sort by (start_ms ASC, end_ms ASC, type ASC, text_snippet ASC)
    highlights.sort(key=lambda h: (
        h["start_ms"],
        h["end_ms"],
        h["type"],
        h["text_snippet"],
    ))

    return highlights


def _merge_warnings(
    step4_report: dict,
    step5_report: dict
) -> List[dict]:
    """
    Merge warnings from Step4 and Step5.

    - Deduplicate by code
    - Keep first message for each code

    Args:
        step4_report: Step4 report dict
        step5_report: Step5 report dict

    Returns:
        Merged warnings list
    """
    seen_codes = set()
    merged = []

    # Process Step4 warnings first
    step4_warnings = step4_report.get("warnings", [])
    for w in step4_warnings:
        if isinstance(w, dict):
            code = w.get("code", "")
            if code not in seen_codes:
                seen_codes.add(code)
                merged.append(w)
        else:
            # Handle legacy string warnings
            code = str(w)
            if code not in seen_codes:
                seen_codes.add(code)
                merged.append({"code": code})

    # Process Step5 warnings
    step5_warnings = step5_report.get("warnings", [])
    for w in step5_warnings:
        if isinstance(w, dict):
            code = w.get("code", "")
            if code not in seen_codes:
                seen_codes.add(code)
                merged.append(w)
        else:
            # Handle legacy string warnings
            code = str(w)
            if code not in seen_codes:
                seen_codes.add(code)
                merged.append({"code": code})

    return merged


def _clean_for_external(report: dict) -> dict:
    """
    Clean report for external output.

    Removes forbidden fields:
    - Any key named 'rule_id'
    - Any key named 'evidence_refs'
    - Root-level 'next_target' (keep only rule_engine.next_target)

    Args:
        report: Report dict to clean

    Returns:
        Cleaned report dict
    """
    # Remove root-level next_target if exists (shouldn't, but safety check)
    if "next_target" in report:
        del report["next_target"]

    return report


def aggregate_report(
    step1_asr: Optional[Dict],
    step2_pace_pause: Optional[Dict],
    step4_rule_engine: dict,
    step5_llm_feedback: dict,
    session: Optional[dict] = None
) -> dict:
    """
    Step6: Aggregate final ReportResponse.

    Args:
        step1_asr: Step1 ASR result (can be None if ASR failed)
        step2_pace_pause: Step2 pace/pause result (can be None)
        step4_rule_engine: Step4 report with rule_engine populated
        step5_llm_feedback: Step5 report with llm_feedback populated
        session: Optional session dict. If None, generates new one.

    Returns:
        Final ReportResponse dict with all required fields:
        - pol_version
        - session
        - scores (single-writer: only Step6 writes overall)
        - rule_engine
        - llm_feedback
        - report_view (chart_data + highlights)
        - warnings (merged)

    Contract:
        - scores.overall is 0-100 number (deterministic)
        - report_view.chart_data.pace_series and pause_series are lists (can be [])
        - report_view.highlights is sorted list
        - warnings is list of {code, message?}
        - No forbidden keys: rule_id, evidence_refs, root next_target
    """
    # Extract rule_engine from Step4
    rule_engine = step4_rule_engine.get("rule_engine", {
        "triggers": [],
        "top_trigger_id": None,
        "next_target": None,
    })

    # Extract llm_feedback from Step5
    llm_feedback = step5_llm_feedback.get("llm_feedback", {"suggestions": []})

    # Compute scores.overall (single-writer)
    triggers = rule_engine.get("triggers", [])
    overall_score = _compute_overall_score(triggers)

    # Build report_view
    pace_series = _build_pace_series(step2_pace_pause)
    pause_series = _build_pause_series(step2_pace_pause)
    highlights = _build_highlights(rule_engine, step1_asr)

    report_view = {
        "chart_data": {
            "pace_series": pace_series,
            "pause_series": pause_series,
        },
        "highlights": highlights,
    }

    # Merge warnings
    warnings = _merge_warnings(step4_rule_engine, step5_llm_feedback)

    # Build session if not provided
    if session is None:
        session = {
            "session_id": str(uuid.uuid4()),
            "task_type": "IMPROV_60S",
            "language": "zh",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Assemble final report
    report = {
        "pol_version": "POL-v0.1",
        "session": session,
        "scores": {
            "overall": overall_score,
        },
        "rule_engine": rule_engine,
        "llm_feedback": llm_feedback,
        "report_view": report_view,
        "warnings": warnings,
    }

    # Clean forbidden fields
    report = _clean_for_external(report)

    return report
