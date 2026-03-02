"""Ranking Contract - 规则排序契约常量."""

# 有效严重性级别
VALID_SEVERITIES = {"P0", "P1", "P2"}

# 严重性排名：P0 > P1 > P2
SEVERITY_RANK = {"P0": 3, "P1": 2, "P2": 1}

# 允许的 Drill ID 白名单
DRILL_ALLOWLIST = {
    "SILENCE_REPLACE",
    "PRESET_OPENERS",
    "REPLACEMENT_BANK",
    "SLOW_10_PERCENT",
    "ONE_LINE_TAKEAWAY",
}

# 规则 ID 到 Drill ID 的映射
# 注意：wpm>190 的分支逻辑在 template_fallback.py 中处理，不在常量里
RULE_ID_TO_DRILL_ID = {
    "BR-OPP-001-R-TASK-001": "ONE_LINE_TAKEAWAY",
    "BR-OPP-001-R-STRUCT-001": "PRESET_OPENERS",
    "BR-OPP-001-R-SPEED-001": "PRESET_OPENERS",
    "BR-OPP-001-R-FILLER-001": "SILENCE_REPLACE",
    "BR-OPP-001-R-REPEAT-001": "REPLACEMENT_BANK",
}

# 必需的映射键（用于验证完整性）
REQUIRED_MAPPING_KEYS = set(RULE_ID_TO_DRILL_ID.keys())

# 禁止的字段名
FORBIDDEN_FIELD_NAMES = {"rule_id", "evidence_refs"}
