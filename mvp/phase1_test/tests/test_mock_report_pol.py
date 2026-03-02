"""Tests for mock_report module - validates Schema compliance."""

from app.mock_report import build_mock_report


def test_mock_report_schema_compliance():
    """Validate that build_mock_report() returns a dict that strictly follows the Schema."""
    report = build_mock_report()
    
    # Check top-level keys exist
    required_keys = {"pol_version", "session", "scores", "rule_engine", "llm_feedback", "warnings"}
    assert required_keys.issubset(report.keys()), f"Missing top-level keys: {required_keys - set(report.keys())}"
    
    # Check warnings is a list and not None
    assert isinstance(report["warnings"], list), "warnings must be a list"
    assert report["warnings"] is not None, "warnings must not be None"
    
    # Check llm_feedback.suggestions is a list
    assert isinstance(report["llm_feedback"]["suggestions"], list), "llm_feedback.suggestions must be a list"
    
    # Check root-level next_target is NOT present (forbidden)
    assert "next_target" not in report, "root-level next_target is forbidden"
    
    # Check rule_engine.next_target exists (can be None)
    assert "next_target" in report["rule_engine"], "rule_engine.next_target must exist"
    
    # Check triggers is a list
    assert isinstance(report["rule_engine"]["triggers"], list), "triggers must be a list"
    
    # Validate each trigger
    required_trigger_fields = {"id", "severity", "impact_score", "weight", "priority_score", 
                               "conflict_priority", "trigger_count", "evidence"}
    valid_severities = {"P0", "P1", "P2"}
    
    for trigger in report["rule_engine"]["triggers"]:
        # Check required fields exist
        assert required_trigger_fields.issubset(trigger.keys()), \
            f"Trigger missing fields: {required_trigger_fields - set(trigger.keys())}"
        
        # Check severity is valid
        assert trigger["severity"] in valid_severities, f"Invalid severity: {trigger['severity']}"
        
        # Check priority_score == impact_score * weight (no clamping)
        expected_priority = trigger["impact_score"] * trigger["weight"]
        assert trigger["priority_score"] == expected_priority, \
            f"priority_score mismatch: {trigger['priority_score']} != {expected_priority}"
        
        # Check evidence.time_ranges is a list
        assert isinstance(trigger["evidence"]["time_ranges"], list), \
            "evidence.time_ranges must be a list"
        
        # Check evidence.text_snippets is a list
        assert isinstance(trigger["evidence"]["text_snippets"], list), \
            "evidence.text_snippets must be a list"
        
        # Check forbidden fields
        assert "rule_id" not in trigger, "rule_id is forbidden in trigger"
        assert "evidence_refs" not in trigger, "evidence_refs is forbidden in trigger"
    
    # Check top_trigger_id equals first trigger's id (when triggers non-empty)
    if report["rule_engine"]["triggers"]:
        assert report["rule_engine"]["top_trigger_id"] == report["rule_engine"]["triggers"][0]["id"], \
            "top_trigger_id must equal first trigger's id"
