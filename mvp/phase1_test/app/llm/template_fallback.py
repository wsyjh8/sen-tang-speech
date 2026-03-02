"""Template fallback for LLM suggestions."""

from typing import Any

from app.contracts import (
    DRILL_ALLOWLIST,
    FORBIDDEN_FIELD_NAMES,
    RULE_ID_TO_DRILL_ID,
    VALID_SEVERITIES,
)

# Rule ID -> Drill ID mapping (alias for backward compatibility in this file)
RULE_TO_DRILL_MAP = RULE_ID_TO_DRILL_ID

# Drill templates
DRILL_TEMPLATES = {
    "SILENCE_REPLACE": {
        "steps": [
            "Identify filler words in your speech (um, uh, like, you know).",
            "Replace each filler with a brief pause (1-2 seconds).",
            "Practice with a recording device to self-monitor.",
            "Review and count filler reduction over multiple sessions."
        ],
        "duration_sec": 300,
        "tips": [
            "Pause is better than filler.",
            "Silence gives emphasis to your words.",
            "Breathe before speaking to reduce fillers."
        ]
    },
    "PRESET_OPENERS": {
        "steps": [
            "Prepare 3-5 standard opening phrases for your topic type.",
            "Practice each opener until it feels natural.",
            "Record yourself and compare different openers.",
            "Select the most engaging opener for your context."
        ],
        "duration_sec": 240,
        "tips": [
            "Start with a hook: question, fact, or story.",
            "Avoid generic greetings like 'Today I will talk about...'",
            "Match opener tone to your audience."
        ]
    },
    "REPLACEMENT_BANK": {
        "steps": [
            "Identify your most frequently repeated words or phrases.",
            "Create a list of synonyms and alternative expressions.",
            "Practice substituting repeats with alternatives.",
            "Get feedback on variety improvement."
        ],
        "duration_sec": 360,
        "tips": [
            "Use a thesaurus to expand vocabulary.",
            "Vary sentence structure, not just words.",
            "Read diverse content to absorb new expressions."
        ]
    },
    "SLOW_10_PERCENT": {
        "steps": [
            "Measure your current speaking rate (WPM).",
            "Set a target 10% slower than current rate.",
            "Practice with a metronome or pacing app.",
            "Record and compare before/after samples."
        ],
        "duration_sec": 420,
        "tips": [
            "Slower speech improves clarity and comprehension.",
            "Pause between key points for emphasis.",
            "Focus on articulation, not just speed."
        ]
    },
    "ONE_LINE_TAKEAWAY": {
        "steps": [
            "Identify the single most important message of your talk.",
            "Craft a concise one-sentence summary (15-20 words).",
            "Place the takeaway at the end of your conclusion.",
            "Practice delivering it with emphasis and pause."
        ],
        "duration_sec": 180,
        "tips": [
            "Make it memorable and actionable.",
            "Use parallel structure for rhythm.",
            "End with a call to action or reflection."
        ]
    }
}

# Acceptance criteria by rule type
ACCEPTANCE_BY_RULE = {
    "BR-OPP-001-R-TASK-001": {
        "metric": "takeaway_present",
        "target": "true",
        "how_to_measure": "system checks ending takeaway in last 10-15s"
    },
    "BR-OPP-001-R-STRUCT-001": {
        "metric": "first_sentence_has_conclusion",
        "target": "true",
        "how_to_measure": "system checks first sentence pattern"
    },
    "BR-OPP-001-R-SPEED-001": {
        "metric": "wpm",
        "target": "120-190",
        "how_to_measure": "system computed wpm"
    },
    "BR-OPP-001-R-FILLER-001": {
        "metric": "filler_ratio",
        "target": "<=3%",
        "how_to_measure": "system counts filler tokens / total tokens"
    },
    "BR-OPP-001-R-REPEAT-001": {
        "metric": "repeat_ratio",
        "target": "<=5%",
        "how_to_measure": "system computes repeated token ratio"
    }
}

# Problem and cause templates by rule type
PROBLEM_CAUSE_TEMPLATES = {
    "BR-OPP-001-R-TASK-001": {
        "title": "Add a Clear Takeaway",
        "problem": "Your speech lacks a memorable closing message.",
        "cause": "Without a takeaway, the audience may forget your main point."
    },
    "BR-OPP-001-R-STRUCT-001": {
        "title": "Improve Opening Structure",
        "problem": "Your opening does not engage the audience effectively.",
        "cause": "Generic openings fail to capture attention in the first 10 seconds."
    },
    "BR-OPP-001-R-SPEED-001": {
        "title": "Adjust Speaking Pace",
        "problem": "Your speaking rate is outside the optimal range.",
        "cause": "Too fast reduces comprehension; too slow loses engagement."
    },
    "BR-OPP-001-R-FILLER-001": {
        "title": "Reduce Filler Words",
        "problem": "Your speech contains excessive filler words.",
        "cause": "Fillers distract the audience and reduce perceived confidence."
    },
    "BR-OPP-001-R-REPEAT-001": {
        "title": "Vary Your Vocabulary",
        "problem": "You repeat the same words or phrases frequently.",
        "cause": "Repetition makes speech sound monotonous and less engaging."
    }
}


def is_known_rule_id(rule_id: str) -> bool:
    """Check if rule_id is in the mapping table."""
    return rule_id in RULE_TO_DRILL_MAP


def get_drill_id(top_trigger_id: str, wpm: float | None = None) -> str:
    """
    Map top_trigger_id to drill_id.
    
    Args:
        top_trigger_id: The rule ID from top trigger.
        wpm: Optional WPM value for SPEED rule.
    
    Returns:
        drill_id from allowlist.
    """
    # Special handling for SPEED rule
    if top_trigger_id == "BR-OPP-001-R-SPEED-001":
        if wpm is not None and wpm > 190:
            return "SLOW_10_PERCENT"
        else:
            return "PRESET_OPENERS"
    
    # Direct mapping
    if top_trigger_id in RULE_ID_TO_DRILL_ID:
        return RULE_ID_TO_DRILL_ID[top_trigger_id]

    # Unknown rule_id -> force ONE_LINE_TAKEAWAY
    return "ONE_LINE_TAKEAWAY"


def build_template_suggestion(
    top_trigger_id: str,
    evidence_ref: dict,
    wpm: float | None = None
) -> dict:
    """
    Build a template suggestion based on top_trigger_id.
    
    Args:
        top_trigger_id: The rule ID from top trigger.
        evidence_ref: Evidence reference to include.
        wpm: Optional WPM value for SPEED rule.
    
    Returns:
        A complete suggestion dict with all required fields.
    """
    drill_id = get_drill_id(top_trigger_id, wpm)
    drill_template = DRILL_TEMPLATES.get(drill_id, DRILL_TEMPLATES["ONE_LINE_TAKEAWAY"])
    
    # Get problem/cause/title from template
    problem_cause = PROBLEM_CAUSE_TEMPLATES.get(
        top_trigger_id,
        PROBLEM_CAUSE_TEMPLATES["BR-OPP-001-R-TASK-001"]
    )
    
    # Get acceptance criteria
    acceptance = ACCEPTANCE_BY_RULE.get(
        top_trigger_id,
        ACCEPTANCE_BY_RULE["BR-OPP-001-R-TASK-001"]
    )
    
    return {
        "title": problem_cause["title"],
        "problem": problem_cause["problem"],
        "cause": problem_cause["cause"],
        "evidence_ref": evidence_ref,
        "drill": {
            "drill_id": drill_id,
            "steps": drill_template["steps"],
            "duration_sec": drill_template["duration_sec"],
            "tips": drill_template["tips"]
        },
        "acceptance": acceptance
    }


def _extract_wpm(top_trigger: dict) -> float | None:
    """
    Extract WPM from top trigger (robust extraction).
    
    Args:
        top_trigger: The top trigger dict.
    
    Returns:
        WPM value or None if not found.
    """
    # Try direct wpm field
    wpm = top_trigger.get("wpm")
    if wpm is not None:
        return wpm
    
    # Try metrics.wpm
    metrics = top_trigger.get("metrics", {})
    if isinstance(metrics, dict):
        wpm = metrics.get("wpm")
        if wpm is not None:
            return wpm
    
    return None


def build_fallback_suggestions(
    report: dict,
    fallback_reason: str
) -> tuple[list[dict], list[str]]:
    """
    Build fallback suggestions when LLM fails or produces low quality.
    
    Args:
        report: The report dict with rule_engine info.
        fallback_reason: Reason for fallback (e.g., "CALL_FAILED:..." or "QUALITY_FALLBACK:...").
    
    Returns:
        (suggestions, warnings_to_add)
    
    Warnings classification:
        - Empty triggers: ["NO_TRIGGERS"]
        - CALL_FAILED: adds "LLM_UNAVAILABLE" + "PARTIAL_REPORT"
        - QUALITY_FALLBACK: adds "PARTIAL_REPORT" only
        - Empty evidence: adds "LOW_EVIDENCE_CONFIDENCE" + "PARTIAL_REPORT"
        - Unknown rule_id: ensures "PARTIAL_REPORT"
    """
    rule_engine = report.get("rule_engine", {})
    triggers = rule_engine.get("triggers", [])
    top_trigger_id = rule_engine.get("top_trigger_id")
    
    warnings_to_add = []
    
    # Handle empty triggers
    if not triggers or top_trigger_id is None:
        warnings_to_add.append("NO_TRIGGERS")
        return [], warnings_to_add
    
    # Get top trigger
    top_trigger = triggers[0]
    
    # Extract WPM for SPEED rule
    wpm = _extract_wpm(top_trigger)
    
    # Build evidence_ref
    evidence = top_trigger.get("evidence", {})
    evidence_ref = {
        "time_ranges": evidence.get("time_ranges", []),
        "text_snippets": evidence.get("text_snippets", [])
    }
    
    # Build template suggestion
    suggestion = build_template_suggestion(top_trigger_id, evidence_ref, wpm)
    
    # Default: always include PARTIAL_REPORT for fallback
    warnings_to_add.append("PARTIAL_REPORT")
    
    # Only add LLM_UNAVAILABLE for CALL_FAILED reasons
    if fallback_reason and fallback_reason.startswith("CALL_FAILED:"):
        warnings_to_add.append("LLM_UNAVAILABLE")
    
    # Check evidence quality
    if not evidence_ref["time_ranges"] and not evidence_ref["text_snippets"]:
        warnings_to_add.append("LOW_EVIDENCE_CONFIDENCE")
        # PARTIAL_REPORT already added
    
    # Unknown rule_id -> ensure PARTIAL_REPORT (already added by default)
    if not is_known_rule_id(top_trigger_id):
        # PARTIAL_REPORT already added
        pass
    
    return [suggestion], warnings_to_add
