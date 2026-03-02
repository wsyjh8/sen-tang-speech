"""Minimal regression runner - validates ranking stability against v0 baseline."""

import json
import sys
from pathlib import Path

from app.mock_report import build_mock_report
from app.rule_engine.top1_ranker import rank_triggers, SEVERITY_RANK, VALID_SEVERITIES
from eval.canonical import canonical_rule_engine


def _reference_sort_key(trigger: dict) -> tuple:
    """Reference sort key matching Frozen Contract."""
    priority_score = trigger["priority_score"]
    severity_rank = SEVERITY_RANK.get(trigger["severity"], 0)
    conflict_priority = trigger["conflict_priority"]
    trigger_count = trigger["trigger_count"]
    return (-priority_score, -severity_rank, conflict_priority, -trigger_count)


def run_min_regression() -> None:
    """
    Run minimal regression test against v0 baseline.
    
    - Reads eval/min_regression_v0.jsonl (one case per line)
    - For each case:
      - Generates report via build_mock_report()
      - Computes canonical_rule_engine(report)
      - Writes artifacts/regression/{case_name}.canon.json
      - Validates all assertions
    - Writes summary: artifacts/regression/summary.txt
    - Any failure raises AssertionError
    """
    base_dir = Path(__file__).parent.parent
    cases_file = base_dir / "eval" / "min_regression_v0.jsonl"
    artifacts_dir = base_dir / "artifacts" / "regression"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Read test cases
    cases = []
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    
    passed = 0
    failed = 0
    errors = []
    
    for case in cases:
        case_name = case["case_name"]
        triggered_triggers = case["triggered_triggers"]
        pack_weights = case.get("pack_weights")
        expected_top_trigger_id = case.get("expected_top_trigger_id")
        expect_priority_gt_one = case.get("expect_priority_gt_one", False)
        
        try:
            # Generate report
            report = build_mock_report(triggered_triggers, pack_weights)
            canonical = canonical_rule_engine(report)
            
            # Write canonical file
            canon_file = artifacts_dir / f"{case_name}.canon.json"
            with open(canon_file, "w", encoding="utf-8") as f:
                f.write(canonical)
            
            # === Assertion 1: Top-level required fields exist ===
            required_top_keys = {"pol_version", "session", "scores", "rule_engine", "llm_feedback", "warnings"}
            assert required_top_keys.issubset(report.keys()), f"Missing top-level keys: {required_top_keys - set(report.keys())}"
            
            # === Assertion 2: warnings is list and not None ===
            assert isinstance(report["warnings"], list), "warnings must be a list"
            assert report["warnings"] is not None, "warnings must not be None"
            
            # === Assertion 3: root-level next_target does NOT exist ===
            assert "next_target" not in report, "root-level next_target is forbidden"
            
            # === Assertion 4: rule_engine.next_target exists (can be None) ===
            assert "next_target" in report["rule_engine"], "rule_engine.next_target must exist"
            
            # === Assertion 5: triggers length matches input ===
            output_triggers = report["rule_engine"]["triggers"]
            assert len(output_triggers) == len(triggered_triggers), \
                f"triggers length mismatch: {len(output_triggers)} != {len(triggered_triggers)}"
            
            # === Assertion 6: Handle empty triggers case ===
            if expected_top_trigger_id is None:
                assert output_triggers == [], "triggers must be empty when no rules triggered"
                assert report["rule_engine"]["top_trigger_id"] is None, "top_trigger_id must be None when no triggers"
            else:
                # === Assertion 7: top_trigger_id matches expected ===
                assert report["rule_engine"]["top_trigger_id"] == expected_top_trigger_id, \
                    f"top_trigger_id mismatch: {report['rule_engine']['top_trigger_id']} != {expected_top_trigger_id}"
            
            # === Assertion 8: Validate each trigger ===
            for trigger in output_triggers:
                # Check required fields
                required_fields = {"id", "severity", "impact_score", "weight", "priority_score", 
                                   "conflict_priority", "trigger_count", "evidence"}
                assert required_fields.issubset(trigger.keys()), \
                    f"Trigger missing fields: {required_fields - set(trigger.keys())}"
                
                # Check severity is valid
                assert trigger["severity"] in VALID_SEVERITIES, \
                    f"Invalid severity: {trigger['severity']}"
                
                # Check priority_score == impact_score * weight
                expected_priority = trigger["impact_score"] * trigger["weight"]
                assert trigger["priority_score"] == expected_priority, \
                    f"priority_score mismatch: {trigger['priority_score']} != {expected_priority}"
                
                # Check weight is correct (pack_weights override or 1.0)
                expected_weight = pack_weights.get(trigger["id"], 1.0) if pack_weights else 1.0
                assert trigger["weight"] == expected_weight, \
                    f"weight mismatch: {trigger['weight']} != {expected_weight}"
                
                # Check forbidden fields
                assert "rule_id" not in trigger, "rule_id is forbidden in trigger"
                assert "evidence_refs" not in trigger, "evidence_refs is forbidden in trigger"
            
            # === Assertion 9: Verify sort order matches reference ===
            if len(output_triggers) > 1:
                # Build reference triggers with computed fields
                ref_triggers = []
                for t in triggered_triggers:
                    tid = t["id"]
                    weight = pack_weights.get(tid, 1.0) if pack_weights else 1.0
                    ref_t = {
                        "id": tid,
                        "priority_score": t["impact_score"] * weight,
                        "severity": t["severity"],
                        "conflict_priority": t["conflict_priority"],
                        "trigger_count": t["trigger_count"],
                    }
                    ref_triggers.append(ref_t)
                ref_triggers.sort(key=_reference_sort_key)
                
                # Compare order by id
                expected_order = [t["id"] for t in ref_triggers]
                actual_order = [t["id"] for t in output_triggers]
                assert actual_order == expected_order, \
                    f"Sort order mismatch: {actual_order} != {expected_order}"
            
            # === Assertion 10: expect_priority_gt_one check ===
            if expect_priority_gt_one:
                has_gt_one = any(t["priority_score"] > 1 for t in output_triggers)
                assert has_gt_one, "At least one priority_score must be > 1"
            
            passed += 1
            
        except AssertionError as e:
            failed += 1
            error_msg = f"Case {case_name}: {str(e)}"
            errors.append(error_msg)
            
            # Write failure file
            fail_file = artifacts_dir / f"{case_name}.fail.txt"
            with open(fail_file, "w", encoding="utf-8") as f:
                f.write(f"Case: {case_name}\n")
                f.write(f"Error: {str(e)}\n")
    
    # Write summary
    summary_file = artifacts_dir / "summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"cases={len(cases)}\n")
        f.write(f"passed={passed}\n")
        f.write(f"failed={failed}\n")
        f.write(f"result={'PASS' if failed == 0 else 'FAIL'}\n")
        if errors:
            f.write("\nErrors:\n")
            for err in errors:
                f.write(f"  - {err}\n")
    
    if failed == 0:
        print(f"[PASS] regression PASS (cases={len(cases)})")
    else:
        print(f"[FAIL] regression FAIL (cases={len(cases)}, passed={passed}, failed={failed})")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


def main() -> None:
    run_min_regression()


if __name__ == "__main__":
    main()
