"""Schema Contract - JSON Schema 契约常量."""

# ReportResponse 顶层必需字段
REQUIRED_REPORT_KEYS = {
    "pol_version",
    "session",
    "scores",
    "rule_engine",
    "llm_feedback",
    "warnings",
}

# rule_engine 对象必需字段
REQUIRED_RULE_ENGINE_KEYS = {
    "triggers",
    "top_trigger_id",
    "next_target",
}

# Trigger 对象必需字段
REQUIRED_TRIGGER_FIELDS = {
    "id",
    "severity",
    "impact_score",
    "weight",
    "priority_score",
    "conflict_priority",
    "trigger_count",
    "evidence",
}

# Evidence 对象必需字段
REQUIRED_EVIDENCE_KEYS = {
    "time_ranges",
    "text_snippets",
}

# Suggestion 对象必需字段
REQUIRED_SUGGESTION_FIELDS = {
    "title",
    "problem",
    "cause",
    "evidence_ref",
    "drill",
    "acceptance",
}

# Evidence Ref 对象必需字段
REQUIRED_EVIDENCE_REF_KEYS = {
    "time_ranges",
    "text_snippets",
}

# Drill 对象必需字段
REQUIRED_DRILL_FIELDS = {
    "drill_id",
    "steps",
    "duration_sec",
    "tips",
}

# Acceptance 对象必需字段
REQUIRED_ACCEPTANCE_FIELDS = {
    "metric",
    "target",
    "how_to_measure",
}
