"""Step4 Integration Layer - wraps top1_ranker into full ReportResponse."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.rule_engine.top1_ranker import rank_triggers
from app.rule_engine.rule_evaluator_top5 import evaluate_top5


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


def step4_from_artifacts(
    step1_result: Dict[str, Any],
    step2_result: Dict[str, Any],
    step3_result: Dict[str, Any],
    pack_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Step4 Integration from Step1-3 artifacts.
    
    Calls evaluate_top5 to generate triggered_triggers from Step1-3 results,
    then calls rank_triggers and returns complete ReportResponse.
    
    Args:
        step1_result: Step1 ASR result
        step2_result: Step2 Pace/Pause result
        step3_result: Step3 Text Features result
        pack_weights: Optional dict mapping trigger.id -> weight override
    
    Returns:
        Complete ReportResponse dict with all required fields.
    """
    # Generate triggered_triggers from artifacts
    triggered_triggers = evaluate_top5(step1_result, step2_result, step3_result)
    
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
