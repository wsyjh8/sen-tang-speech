"""Schema validation for LLM suggestions."""

from typing import Any

from app.contracts import (
    DRILL_ALLOWLIST,
    REQUIRED_ACCEPTANCE_FIELDS,
    REQUIRED_DRILL_FIELDS,
    REQUIRED_EVIDENCE_REF_KEYS,
    REQUIRED_SUGGESTION_FIELDS,
)

# Aliases for backward compatibility in this file
REQUIRED_EVIDENCE_REF_FIELDS = REQUIRED_EVIDENCE_REF_KEYS
DRILL_ID_ALLOWLIST = DRILL_ALLOWLIST


def validate_suggestions(suggestions: Any) -> tuple[bool, str | None]:
    """
    Validate suggestions array.
    
    Args:
        suggestions: The suggestions array from LLM response.
    
    Returns:
        (ok, reason): ok=True if valid, reason=None.
                      ok=False if invalid, reason=description of failure.
    """
    # Check suggestions is a list
    if not isinstance(suggestions, list):
        return False, "suggestions must be a list"
    
    # Check length 1-3
    if len(suggestions) < 1 or len(suggestions) > 3:
        return False, f"suggestions length must be 1-3, got {len(suggestions)}"
    
    for i, suggestion in enumerate(suggestions):
        # Check required top-level fields
        if not isinstance(suggestion, dict):
            return False, f"suggestion[{i}] must be a dict"
        
        missing_fields = REQUIRED_SUGGESTION_FIELDS - set(suggestion.keys())
        if missing_fields:
            return False, f"suggestion[{i}] missing fields: {missing_fields}"
        
        # Validate evidence_ref
        evidence_ref = suggestion.get("evidence_ref")
        if not isinstance(evidence_ref, dict):
            return False, f"suggestion[{i}].evidence_ref must be a dict"
        
        missing_evidence = REQUIRED_EVIDENCE_REF_FIELDS - set(evidence_ref.keys())
        if missing_evidence:
            return False, f"suggestion[{i}].evidence_ref missing fields: {missing_evidence}"
        
        # Validate drill
        drill = suggestion.get("drill")
        if not isinstance(drill, dict):
            return False, f"suggestion[{i}].drill must be a dict"
        
        missing_drill = REQUIRED_DRILL_FIELDS - set(drill.keys())
        if missing_drill:
            return False, f"suggestion[{i}].drill missing fields: {missing_drill}"
        
        # Check drill_id in allowlist
        drill_id = drill.get("drill_id")
        if drill_id not in DRILL_ID_ALLOWLIST:
            return False, f"suggestion[{i}].drill.drill_id '{drill_id}' not in allowlist"
        
        # Validate acceptance
        acceptance = suggestion.get("acceptance")
        if not isinstance(acceptance, dict):
            return False, f"suggestion[{i}].acceptance must be a dict"
        
        missing_acceptance = REQUIRED_ACCEPTANCE_FIELDS - set(acceptance.keys())
        if missing_acceptance:
            return False, f"suggestion[{i}].acceptance missing fields: {missing_acceptance}"
    
    return True, None


def validate_evidence_quality(evidence_ref: dict) -> tuple[bool, str | None]:
    """
    Check evidence quality (low quality triggers fallback).
    
    Args:
        evidence_ref: The evidence_ref dict from suggestion.
    
    Returns:
        (ok, reason): ok=True if quality is acceptable.
    """
    time_ranges = evidence_ref.get("time_ranges", [])
    text_snippets = evidence_ref.get("text_snippets", [])
    
    # Both arrays empty -> low quality
    if not time_ranges and not text_snippets:
        return False, "evidence_ref.time_ranges and text_snippets are both empty"
    
    return True, None
