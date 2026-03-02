# Contracts - 契约常量唯一来源
"""
Contracts module - single source of truth for constants.

Usage:
    from app.contracts import (
        VALID_SEVERITIES,
        SEVERITY_RANK,
        DRILL_ALLOWLIST,
        REQUIRED_REPORT_KEYS,
        ...
    )
"""

from app.contracts.ranking_contract import (
    VALID_SEVERITIES,
    SEVERITY_RANK,
    DRILL_ALLOWLIST,
    RULE_ID_TO_DRILL_ID,
    REQUIRED_MAPPING_KEYS,
    FORBIDDEN_FIELD_NAMES,
)

from app.contracts.schema_contract import (
    REQUIRED_REPORT_KEYS,
    REQUIRED_RULE_ENGINE_KEYS,
    REQUIRED_TRIGGER_FIELDS,
    REQUIRED_EVIDENCE_KEYS,
    REQUIRED_SUGGESTION_FIELDS,
    REQUIRED_EVIDENCE_REF_KEYS,
    REQUIRED_DRILL_FIELDS,
    REQUIRED_ACCEPTANCE_FIELDS,
)

__all__ = [
    # ranking_contract
    "VALID_SEVERITIES",
    "SEVERITY_RANK",
    "DRILL_ALLOWLIST",
    "RULE_ID_TO_DRILL_ID",
    "REQUIRED_MAPPING_KEYS",
    "FORBIDDEN_FIELD_NAMES",
    # schema_contract
    "REQUIRED_REPORT_KEYS",
    "REQUIRED_RULE_ENGINE_KEYS",
    "REQUIRED_TRIGGER_FIELDS",
    "REQUIRED_EVIDENCE_KEYS",
    "REQUIRED_SUGGESTION_FIELDS",
    "REQUIRED_EVIDENCE_REF_KEYS",
    "REQUIRED_DRILL_FIELDS",
    "REQUIRED_ACCEPTANCE_FIELDS",
]
