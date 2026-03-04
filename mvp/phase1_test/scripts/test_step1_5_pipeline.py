"""Test script to run Step1-5 pipeline and output JSON."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.full_pipeline import run_step1_to_step5


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/test_16k.wav"
    use_llm = sys.argv[2] == "1" if len(sys.argv) > 2 else False
    
    print(f"Running Step1-5 pipeline...")
    print(f"Audio: {audio_path}")
    print(f"Use LLM: {use_llm}")
    
    report = run_step1_to_step5(audio_path, use_llm=use_llm)
    
    # Save full JSON
    output_path = Path(__file__).parent.parent / "artifacts" / "step1_5_demo_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nReport saved to: {output_path}")
    print(f"pol_version: {report.get('pol_version')}")
    print(f"triggers count: {len(report.get('rule_engine', {}).get('triggers', []))}")
    print(f"top_trigger_id: {report.get('rule_engine', {}).get('top_trigger_id')}")
    print(f"suggestions count: {len(report.get('llm_feedback', {}).get('suggestions', []))}")


if __name__ == "__main__":
    main()
