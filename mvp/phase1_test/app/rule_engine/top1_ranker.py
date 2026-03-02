"""Top-1 Ranker for rule engine - implements Frozen Contract sorting."""

from typing import Optional

from app.contracts import SEVERITY_RANK, VALID_SEVERITIES


def _sort_key(trigger: dict) -> tuple:
    """
    Generate sort key for a trigger according to Frozen Contract.
    
    Sorting order (DESC means higher first, ASC means lower first):
    - primary: priority_score DESC (negate for DESC sort)
    - tie-break 1: severity DESC (P0 > P1 > P2)
    - tie-break 2: conflict_priority ASC (1 is highest)
    - tie-break 3: trigger_count DESC
    """
    priority_score = trigger["priority_score"]
    severity_rank = SEVERITY_RANK.get(trigger["severity"], 0)
    conflict_priority = trigger["conflict_priority"]
    trigger_count = trigger["trigger_count"]
    
    # Use negative for DESC sort (Python sorts ASC by default)
    return (-priority_score, -severity_rank, conflict_priority, -trigger_count)


def rank_triggers(
    triggered_triggers: list[dict],
    pack_weights: Optional[dict] = None
) -> dict:
    """
    Rank triggered rules according to Frozen Contract.
    
    Args:
        triggered_triggers: List of trigger inputs with fields:
            - id, impact_score, severity, conflict_priority, trigger_count, evidence
        pack_weights: Optional dict mapping trigger.id -> weight override
    
    Returns:
        dict with rule_engine structure:
        {
            "triggers": [...ordered...],
            "top_trigger_id": str | None,
            "next_target": None
        }
    
    Contract:
        - weight = pack_weights.get(id, 1.0)
        - priority_score = impact_score * weight (no clamp/normalize)
        - Sort by priority_score DESC, then severity DESC, conflict_priority ASC, trigger_count DESC
    """
    if pack_weights is None:
        pack_weights = {}
    
    # Build output triggers with computed fields
    output_triggers = []
    for t in triggered_triggers:
        trigger_id = t["id"]
        impact_score = t["impact_score"]
        severity = t["severity"]
        conflict_priority = t["conflict_priority"]
        trigger_count = t["trigger_count"]
        evidence = t.get("evidence", {"time_ranges": [], "text_snippets": []})
        
        # Compute weight and priority_score
        weight = pack_weights.get(trigger_id, 1.0)
        priority_score = impact_score * weight
        
        output_trigger = {
            "id": trigger_id,
            "severity": severity,
            "impact_score": impact_score,
            "weight": weight,
            "priority_score": priority_score,
            "conflict_priority": conflict_priority,
            "trigger_count": trigger_count,
            "evidence": evidence,
        }
        output_triggers.append(output_trigger)
    
    # Sort according to Frozen Contract
    output_triggers.sort(key=_sort_key)
    
    # Determine top_trigger_id
    top_trigger_id = output_triggers[0]["id"] if output_triggers else None
    
    return {
        "triggers": output_triggers,
        "top_trigger_id": top_trigger_id,
        "next_target": None,
    }
