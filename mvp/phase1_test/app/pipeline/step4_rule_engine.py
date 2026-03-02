"""Step4 Integration Layer - wraps top1_ranker into full ReportResponse."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.rule_engine.top1_ranker import rank_triggers


def step4_rule_engine(
    triggered_triggers: list[dict],
    pack_weights: Optional[dict] = None
) -> dict:
    """
    Step4 Integration Layer: receives triggered_triggers + pack_weights,
    calls rank_triggers, and returns a complete ReportResponse.
    
    Args:
        triggered_triggers: List of trigger inputs with fields:
            - id, impact_score, severity, conflict_priority, trigger_count, evidence
        pack_weights: Optional dict mapping trigger.id -> weight override
    
    Returns:
        Complete ReportResponse dict with all required fields:
        - pol_version: "POL-v0.1"
        - session: object
        - scores: {"overall": number}
        - rule_engine: {triggers, top_trigger_id, next_target}
        - llm_feedback: {"suggestions": []}
        - warnings: []
    
    Contract:
        - Does NOT introduce evidence_refs or rule_id
        - root-level next_target does NOT exist
        - All triggered rules are returned (no truncation)
    """
    # Call the core ranking function
    rule_engine = rank_triggers(triggered_triggers, pack_weights)
    
    # Build complete ReportResponse
    report = {
        "pol_version": "POL-v0.1",
        "session": {
            "session_id": str(uuid.uuid4()),
            "task_type": "IMPROV_60S",
            "language": "zh",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "scores": {
            "overall": 80,
        },
        "rule_engine": rule_engine,
        "llm_feedback": {
            "suggestions": [],
        },
        "warnings": [],
    }
    
    return report
