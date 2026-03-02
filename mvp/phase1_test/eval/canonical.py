"""Canonical dump utilities for determinism comparison."""

import json


def canonical_rule_engine(report: dict) -> str:
    """
    Generate a canonical string representation of rule_engine for determinism comparison.
    
    Only includes:
    - top_trigger_id
    - triggers list (in current output order), each with:
      - id (string)
      - severity (string "P0"/"P1"/"P2")
      - impact_score (float, rounded to 6 decimals)
      - weight (float, rounded to 6 decimals)
      - priority_score (float, rounded to 6 decimals)
      - conflict_priority (int)
      - trigger_count (int)
    
    Output format:
    - Fixed key order (via sort_keys=True)
    - Fixed float precision (round to 6 decimals)
    - Compact JSON (separators=(",",":"))
    """
    rule_engine = report["rule_engine"]
    
    canonical_triggers = []
    for trigger in rule_engine["triggers"]:
        canonical_trigger = {
            "conflict_priority": trigger["conflict_priority"],
            "id": trigger["id"],
            "impact_score": round(trigger["impact_score"], 6),
            "priority_score": round(trigger["priority_score"], 6),
            "severity": trigger["severity"],
            "trigger_count": trigger["trigger_count"],
            "weight": round(trigger["weight"], 6),
        }
        canonical_triggers.append(canonical_trigger)
    
    canonical_obj = {
        "top_trigger_id": rule_engine["top_trigger_id"],
        "triggers": canonical_triggers,
    }
    
    return json.dumps(canonical_obj, sort_keys=True, separators=(",", ":"))
