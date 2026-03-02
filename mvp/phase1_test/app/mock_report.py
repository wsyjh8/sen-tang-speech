"""Mock ReportResponse generator - wraps Step4 integration layer."""

from typing import Optional

from app.pipeline.step4_rule_engine import step4_rule_engine


# Default case1 data for backward compatibility
_DEFAULT_TRIGGERED_TRIGGERS = [
    {"id": "r_a", "impact_score": 0.2, "severity": "P1", "conflict_priority": 3, "trigger_count": 1, "evidence": {"time_ranges": [], "text_snippets": []}},
    {"id": "r_b", "impact_score": 0.5, "severity": "P0", "conflict_priority": 1, "trigger_count": 5, "evidence": {"time_ranges": [], "text_snippets": []}},
    {"id": "r_c", "impact_score": 0.5, "severity": "P0", "conflict_priority": 1, "trigger_count": 10, "evidence": {"time_ranges": [], "text_snippets": []}},
]


def build_mock_report(
    triggered_triggers: Optional[list[dict]] = None,
    pack_weights: Optional[dict] = None
) -> dict:
    """
    Build a mock ReportResponse dict using Step4 integration layer.
    
    Args:
        triggered_triggers: List of trigger inputs. If None, uses default case1 data.
        pack_weights: Optional dict mapping trigger.id -> weight override.
    
    Returns:
        ReportResponse dict with all required fields.
    """
    if triggered_triggers is None:
        triggered_triggers = _DEFAULT_TRIGGERED_TRIGGERS
    
    return step4_rule_engine(triggered_triggers, pack_weights)
