"""Determinism replay runner - validates ranking stability across multiple replays."""

import argparse
import copy
import json
import random
import sys
from pathlib import Path

from app.mock_report import build_mock_report
from eval.canonical import canonical_rule_engine


def _load_case(case_name: str) -> dict:
    """Load a specific case from min_regression_v0.jsonl."""
    base_dir = Path(__file__).parent.parent
    cases_file = base_dir / "eval" / "min_regression_v0.jsonl"
    
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                case = json.loads(line)
                if case["case_name"] == case_name:
                    return case
    
    raise ValueError(f"Case not found: {case_name}")


def run_determinism(replays: int = 20, case_name: str = "case1_multiple_rules_triggered") -> None:
    """
    Run determinism test with N replays.
    
    - Loads specified case from min_regression_v0.jsonl
    - Each replay:
      - Deep copies triggered_triggers
      - Shuffles the copy using random.Random(i).shuffle()
      - Runs ranking to get report -> canonical string
    - First replay serves as baseline
    - Subsequent replays must match baseline exactly
    - Any drift raises AssertionError and writes diff file
    """
    # Load case
    case = _load_case(case_name)
    triggered_triggers = case["triggered_triggers"]
    pack_weights = case.get("pack_weights")
    
    # Setup artifacts directory
    artifacts_dir = Path(__file__).parent.parent / "artifacts" / "determinism"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    baseline_canonical = None
    
    for i in range(replays):
        # Deep copy and shuffle triggered_triggers
        shuffled_triggers = copy.deepcopy(triggered_triggers)
        random.Random(i).shuffle(shuffled_triggers)
        
        # Generate report with shuffled input
        report = build_mock_report(shuffled_triggers, pack_weights)
        canonical = canonical_rule_engine(report)
        
        # Write replay canonical file
        replay_file = artifacts_dir / f"replay_{i:02d}.canon.json"
        with open(replay_file, "w", encoding="utf-8") as f:
            f.write(canonical)
        
        if i == 0:
            baseline_canonical = canonical
        else:
            # Compare with baseline
            if canonical != baseline_canonical:
                # Write diff file
                diff_file = artifacts_dir / f"drift_{i:02d}.txt"
                with open(diff_file, "w", encoding="utf-8") as f:
                    f.write(f"=== DRIFT DETECTED at replay {i} ===\n\n")
                    f.write(f"--- baseline (replay_00) ---\n{baseline_canonical}\n\n")
                    f.write(f"+++ current (replay_{i:02d}) +++\n{canonical}\n")
                
                raise AssertionError(f"Determinism drift detected at replay {i}")
    
    # Write summary
    summary_file = artifacts_dir / "summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"replays={replays}\n")
        f.write(f"case_name={case_name}\n")
        f.write("result=PASS\n")
    
    print(f"[PASS] determinism PASS (replays={replays})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run determinism replay test")
    parser.add_argument(
        "--replays",
        type=int,
        default=20,
        help="Number of replays to run (default: 20)"
    )
    parser.add_argument(
        "--case_name",
        type=str,
        default="case1_multiple_rules_triggered",
        help="Case name to use for determinism test (default: case1_multiple_rules_triggered)"
    )
    args = parser.parse_args()
    
    run_determinism(replays=args.replays, case_name=args.case_name)


if __name__ == "__main__":
    main()
