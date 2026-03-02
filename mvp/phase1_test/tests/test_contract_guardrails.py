"""Contract Guardrails - 验证契约常量的一致性."""

from app.contracts import (
    DRILL_ALLOWLIST,
    FORBIDDEN_FIELD_NAMES,
    REQUIRED_MAPPING_KEYS,
    RULE_ID_TO_DRILL_ID,
    SEVERITY_RANK,
    VALID_SEVERITIES,
)


def test_required_mapping_keys_complete():
    """验证 REQUIRED_MAPPING_KEYS 与 RULE_ID_TO_DRILL_ID 的键一致."""
    assert REQUIRED_MAPPING_KEYS == set(RULE_ID_TO_DRILL_ID.keys()), \
        "REQUIRED_MAPPING_KEYS must match RULE_ID_TO_DRILL_ID keys"


def test_valid_severities_match_severity_rank():
    """验证 VALID_SEVERITIES 与 SEVERITY_RANK 的键一致."""
    assert VALID_SEVERITIES == set(SEVERITY_RANK.keys()), \
        "VALID_SEVERITIES must match SEVERITY_RANK keys"


def test_forbidden_field_names():
    """验证 FORBIDDEN_FIELD_NAMES 包含必需的禁止字段."""
    assert "rule_id" in FORBIDDEN_FIELD_NAMES, \
        "'rule_id' must be in FORBIDDEN_FIELD_NAMES"
    assert "evidence_refs" in FORBIDDEN_FIELD_NAMES, \
        "'evidence_refs' must be in FORBIDDEN_FIELD_NAMES"


def test_drill_allowlist_not_empty():
    """验证 DRILL_ALLOWLIST 非空."""
    assert len(DRILL_ALLOWLIST) > 0, "DRILL_ALLOWLIST must not be empty"


def test_rule_id_to_drill_id_values_in_allowlist():
    """验证 RULE_ID_TO_DRILL_ID 的所有值都在 DRILL_ALLOWLIST 中."""
    for rule_id, drill_id in RULE_ID_TO_DRILL_ID.items():
        assert drill_id in DRILL_ALLOWLIST, \
            f"drill_id '{drill_id}' for rule '{rule_id}' not in DRILL_ALLOWLIST"


def test_severity_rank_values_are_positive():
    """验证 SEVERITY_RANK 的所有值都是正整数."""
    for severity, rank in SEVERITY_RANK.items():
        assert isinstance(rank, int) and rank > 0, \
            f"severity rank for '{severity}' must be positive integer"
