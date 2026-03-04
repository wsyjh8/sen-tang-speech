"""Step5 LLM Feedback - integrates LLM suggestions into report."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.llm.prm_v0_1 import (
    PRM_VERSION, build_messages, compute_hash,
    TRANSCRIPT_SNIPPETS_MAX_CHARS
)
from app.llm.redaction import redact
from app.llm.client import call_llm, parse_llm_response, LLMUnavailableError
from app.llm.schema_validate import validate_suggestions, validate_evidence_quality
from app.llm.template_fallback import build_fallback_suggestions, is_known_rule_id
from app.llm.trace import write_trace


def _extract_transcript_snippets(report: dict) -> str:
    """
    Extract and redact transcript snippets from report.
    
    Args:
        report: The report dict.
    
    Returns:
        Redacted transcript snippets (<=1200 chars).
    """
    # For now, extract from triggers' evidence
    rule_engine = report.get("rule_engine", {})
    triggers = rule_engine.get("triggers", [])
    
    snippets = []
    total_chars = 0
    
    for trigger in triggers:
        evidence = trigger.get("evidence", {})
        text_snippets = evidence.get("text_snippets", [])
        for snippet in text_snippets:
            if total_chars >= TRANSCRIPT_SNIPPETS_MAX_CHARS:
                break
            snippets.append(snippet)
            total_chars += len(snippet)
    
    # Join and truncate
    combined = "\n".join(snippets)
    if len(combined) > TRANSCRIPT_SNIPPETS_MAX_CHARS:
        combined = combined[:TRANSCRIPT_SNIPPETS_MAX_CHARS]
    
    # Redact sensitive info
    return redact(combined)


def _build_evidence_ref(top_trigger: dict) -> dict:
    """
    Build evidence_ref from top trigger.
    
    Args:
        top_trigger: The top trigger dict.
    
    Returns:
        evidence_ref dict with time_ranges and text_snippets.
    """
    evidence = top_trigger.get("evidence", {})
    return {
        "time_ranges": evidence.get("time_ranges", []),
        "text_snippets": evidence.get("text_snippets", [])
    }


def step5_llm_feedback(report: dict, use_llm: bool = True) -> dict:
    """
    Step5: Add LLM feedback to report.

    Args:
        report: Report from Step4 with rule_engine populated.
        use_llm: If False, skip LLM call and use template fallback directly.

    Returns:
        Report with llm_feedback.suggestions populated.

    Process:
        1. Get top_trigger_id and evidence
        2. Prepare transcript snippets (redacted, <=1200 chars)
        3. If use_llm=False, skip to fallback
        4. Call LLM or fallback to template
        5. Validate suggestions
        6. Write trace (exactly once)
        7. Add warnings as needed
    """
    rule_engine = report.get("rule_engine", {})
    triggers = rule_engine.get("triggers", [])
    top_trigger_id = rule_engine.get("top_trigger_id")

    warnings = list(report.get("warnings", []))

    # Handle empty triggers
    if not triggers or top_trigger_id is None:
        warnings.append("NO_TRIGGERS")
        report["llm_feedback"] = {"suggestions": []}
        report["warnings"] = warnings
        return report

    # Get top trigger
    top_trigger = triggers[0]
    evidence_ref = _build_evidence_ref(top_trigger)

    # Prepare transcript snippets
    transcript_snippets = _extract_transcript_snippets(report)

    # Build messages with metrics
    pol_version = report.get("pol_version", "POL-v0.1")
    
    # Extract metrics from step2/step3 data (if available in report)
    metrics = {}
    # Try to get metrics from report's internal storage (if any)
    # For now, use defaults
    wpm = report.get("_step2_wpm")
    filler_ratio = report.get("_step3_filler_ratio")
    repeat_ratio = report.get("_step3_repeat_ratio")
    long_pause_count = report.get("_step2_long_pause_count")
    max_pause_ms = report.get("_step2_max_pause_ms")
    
    if wpm is not None:
        metrics["wpm"] = wpm
    if filler_ratio is not None:
        metrics["filler_ratio"] = filler_ratio
    if repeat_ratio is not None:
        metrics["repeat_ratio"] = repeat_ratio
    if long_pause_count is not None:
        metrics["long_pause_count"] = long_pause_count
    if max_pause_ms is not None:
        metrics["max_pause_ms"] = max_pause_ms
    
    messages = build_messages(
        pol_version=pol_version,
        top_trigger_id=top_trigger_id,
        top_trigger_evidence=top_trigger.get("evidence"),
        transcript_snippets=transcript_snippets,
        metrics=metrics
    )

    request_id = str(uuid.uuid4())
    suggestions = None
    fallback_reason = None
    trace_fields = {
        "request_id": request_id,
        "prm_version": PRM_VERSION,
        "pol_version": pol_version,
    }

    # Check if LLM is forced off
    if not use_llm:
        fallback_reason = "CALL_FAILED:FORCED_FALLBACK"
        trace_fields["fallback_reason"] = fallback_reason
    else:
        try:
            # Call LLM
            response_text, call_trace = call_llm(messages, request_id)
            trace_fields.update(call_trace)

            # Parse response
            response_data = parse_llm_response(response_text)
            suggestions = response_data.get("suggestions")

            # Validate suggestions
            if suggestions is None:
                raise ValueError("suggestions field missing from response")

            ok, reason = validate_suggestions(suggestions)
            if not ok:
                raise ValueError(f"Invalid suggestions: {reason}")

            # Validate evidence quality
            for suggestion in suggestions:
                ev_ref = suggestion.get("evidence_ref", {})
                ok, reason = validate_evidence_quality(ev_ref)
                if not ok:
                    raise ValueError(f"Low evidence quality: {reason}")

            # Compute output_hash using canonical JSON
            canonical = json.dumps(suggestions, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            trace_fields["output_hash"] = compute_hash(canonical)

        except LLMUnavailableError as e:
            # Capture trace_fields from exception
            if hasattr(e, "trace_fields"):
                trace_fields.update(e.trace_fields)
            fallback_reason = f"CALL_FAILED:{str(e)}"
            trace_fields["fallback_reason"] = fallback_reason
        except Exception as e:
            fallback_reason = f"QUALITY_FALLBACK:{str(e)}"
            trace_fields["fallback_reason"] = fallback_reason

    # Check for unknown rule_id before fallback
    if not is_known_rule_id(top_trigger_id):
        if trace_fields.get("fallback_reason"):
            trace_fields["fallback_reason"] += "|UNKNOWN_RULE_ID"
        else:
            trace_fields["fallback_reason"] = "UNKNOWN_RULE_ID"

    # Apply fallback if needed
    if suggestions is None:
        suggestions, fallback_warnings = build_fallback_suggestions(
            report, fallback_reason
        )
        warnings.extend(fallback_warnings)

        # Compute output_hash for fallback suggestions
        canonical = json.dumps(suggestions, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        trace_fields["output_hash"] = compute_hash(canonical)

    # Ensure output_hash is set
    if "output_hash" not in trace_fields:
        trace_fields["output_hash"] = ""

    # Ensure latency_ms is set
    trace_fields["latency_ms"] = 0

    # Write trace exactly once
    write_trace(trace_fields)

    # Update report
    report["llm_feedback"] = {"suggestions": suggestions}
    report["warnings"] = warnings

    return report
