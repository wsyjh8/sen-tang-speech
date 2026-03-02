"""Unit tests for Top1Ranker - validates Frozen Contract sorting."""

from app.rule_engine.top1_ranker import rank_triggers


def _validate_common_assertions(rule_engine: dict) -> None:
    """
    Common assertions for all tests.
    
    Args:
        rule_engine: The dict returned by rank_triggers(), which is the rule_engine content.
    """
    # Check rule_engine.next_target exists and is None
    assert "next_target" in rule_engine, "rule_engine.next_target must exist"
    assert rule_engine["next_target"] is None, "rule_engine.next_target must be None"
    
    # Check each trigger does not contain forbidden fields
    for trigger in rule_engine["triggers"]:
        assert "rule_id" not in trigger, "rule_id is forbidden in trigger"
        assert "evidence_refs" not in trigger, "evidence_refs is forbidden in trigger"


def test_ut_a_impact_score_dominant() -> None:
    """
    UT-A: impact_score dominates when weight is same (pack_weights=None).
    
    Two triggers:
    - low_impact: impact=0.2, severity=P0 (higher), conflict_priority=1, trigger_count=10
    - high_impact: impact=0.9, severity=P2 (lower), conflict_priority=2, trigger_count=1
    
    Expected: high_impact wins because priority_score (0.9) > low_impact (0.2)
    """
    triggered_triggers = [
        {
            "id": "low_impact",
            "impact_score": 0.2,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 10,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
        {
            "id": "high_impact",
            "impact_score": 0.9,
            "severity": "P2",
            "conflict_priority": 2,
            "trigger_count": 1,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
    ]
    
    result = rank_triggers(triggered_triggers, pack_weights=None)
    rule_engine = result
    
    _validate_common_assertions(rule_engine)
    
    # Expected top_trigger_id
    assert rule_engine["top_trigger_id"] == "high_impact", \
        "high_impact should win due to higher priority_score"
    
    # Validate weight and priority_score for each trigger
    triggers = rule_engine["triggers"]
    assert len(triggers) == 2
    
    for t in triggers:
        # weight must be 1.0 (default)
        assert t["weight"] == 1.0, f"weight must be 1.0, got {t['weight']}"
        # priority_score must equal impact_score * weight
        expected_priority = t["impact_score"] * t["weight"]
        assert t["priority_score"] == expected_priority, \
            f"priority_score mismatch: {t['priority_score']} != {expected_priority}"


def test_ut_b_weight_override_flips_top1() -> None:
    """
    UT-B: weight override flips Top1 and priority_score > 1.
    
    Two triggers:
    - base_high: impact=0.8, weight=1.0 (default) => priority_score=0.8
    - boosted: impact=0.7, weight=2.0 (override) => priority_score=1.4
    
    Expected: boosted wins because 1.4 > 0.8
    """
    triggered_triggers = [
        {
            "id": "base_high",
            "impact_score": 0.8,
            "severity": "P1",
            "conflict_priority": 2,
            "trigger_count": 5,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
        {
            "id": "boosted",
            "impact_score": 0.7,
            "severity": "P2",
            "conflict_priority": 4,
            "trigger_count": 3,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
    ]
    
    pack_weights = {"boosted": 2.0}
    
    result = rank_triggers(triggered_triggers, pack_weights=pack_weights)
    rule_engine = result
    
    _validate_common_assertions(rule_engine)
    
    # Expected top_trigger_id
    assert rule_engine["top_trigger_id"] == "boosted", \
        "boosted should win due to weight override"
    
    triggers = rule_engine["triggers"]
    assert len(triggers) == 2
    
    # Find boosted trigger and validate
    boosted_trigger = next(t for t in triggers if t["id"] == "boosted")
    
    # Validate weight is overridden
    assert boosted_trigger["weight"] == 2.0, \
        f"boosted weight must be 2.0, got {boosted_trigger['weight']}"
    
    # Validate priority_score > 1
    assert boosted_trigger["priority_score"] > 1.0, \
        f"boosted priority_score must be > 1.0, got {boosted_trigger['priority_score']}"
    
    # Validate priority_score == impact_score * weight (no clamp)
    expected_priority = boosted_trigger["impact_score"] * boosted_trigger["weight"]
    assert boosted_trigger["priority_score"] == expected_priority, \
        f"priority_score mismatch: {boosted_trigger['priority_score']} != {expected_priority}"
    
    # Validate base_high has default weight
    base_trigger = next(t for t in triggers if t["id"] == "base_high")
    assert base_trigger["weight"] == 1.0, \
        f"base_high weight must be 1.0, got {base_trigger['weight']}"


def test_ut_c_tie_break_chain() -> None:
    """
    UT-C: priority_score identical, validate full tie-break chain.
    
    Four triggers with impact_score=1.0 and weight=1.0, so priority_score=1.0 for all:
    - higher_tc: severity="P0", conflict_priority=1, trigger_count=10   (should be 1st)
    - lower_tc:  severity="P0", conflict_priority=1, trigger_count=5    (should be 2nd)
    - higher_cp: severity="P0", conflict_priority=2, trigger_count=999  (should be 3rd)
    - low_sev:   severity="P2", conflict_priority=1, trigger_count=999  (should be 4th)
    
    Tie-break order:
    1. severity DESC (P0 > P1 > P2)
    2. conflict_priority ASC (1 is highest)
    3. trigger_count DESC
    
    Expected order: ["higher_tc", "lower_tc", "higher_cp", "low_sev"]
    """
    triggered_triggers = [
        {
            "id": "higher_tc",
            "impact_score": 1.0,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 10,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
        {
            "id": "lower_tc",
            "impact_score": 1.0,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 5,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
        {
            "id": "higher_cp",
            "impact_score": 1.0,
            "severity": "P0",
            "conflict_priority": 2,
            "trigger_count": 999,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
        {
            "id": "low_sev",
            "impact_score": 1.0,
            "severity": "P2",
            "conflict_priority": 1,
            "trigger_count": 999,
            "evidence": {"time_ranges": [], "text_snippets": []},
        },
    ]
    
    result = rank_triggers(triggered_triggers, pack_weights=None)
    rule_engine = result
    
    _validate_common_assertions(rule_engine)
    
    # Expected order
    expected_order = ["higher_tc", "lower_tc", "higher_cp", "low_sev"]
    actual_order = [t["id"] for t in rule_engine["triggers"]]
    
    assert actual_order == expected_order, \
        f"Tie-break order mismatch: {actual_order} != {expected_order}"
    
    # Validate all have same priority_score
    triggers = rule_engine["triggers"]
    assert len(triggers) == 4
    
    for t in triggers:
        # All should have priority_score == 1.0
        assert t["priority_score"] == 1.0, \
            f"priority_score must be 1.0, got {t['priority_score']}"
        # All should have weight == 1.0
        assert t["weight"] == 1.0, \
            f"weight must be 1.0, got {t['weight']}"
