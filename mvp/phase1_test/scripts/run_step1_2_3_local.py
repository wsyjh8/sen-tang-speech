"""
CLI script to run Step1-2-3 pipeline on local audio file.

Usage:
    python scripts/run_step1_2_3_local.py --audio <path> [--out_dir artifacts]

Behavior:
1) Run Step1 ASR -> save artifacts/step1_asr.json
2) Run Step2 Pace/Pause (with step1_result for wpm) -> save artifacts/step2_pace_pause.json
3) Run Step3 Text Features (with step1_result + step2_result) -> save artifacts/step3_text_features.json
4) Print summary
5) Write bundle: artifacts/step1_2_3_bundle.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from app.asr.step1_asr import run_step1_asr
from app.acoustic.step2_pace_pause import run_step2_pace_pause
from app.text_features.step3_text_features import run_step3_text_features


def save_json(data: Dict[str, Any], path: Path) -> None:
    """Save dict to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Run Step1-2-3 pipeline on local audio")
    parser.add_argument("--audio", required=True, help="Path to local audio file (WAV 16kHz mono 16-bit)")
    parser.add_argument(
        "--out_dir",
        default="artifacts",
        help="Output directory (default: artifacts)"
    )
    
    args = parser.parse_args()
    
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # ========== Step1: ASR ==========
    print("=" * 50)
    print("Step1: Running ASR...")
    step1_result = run_step1_asr(audio_path=args.audio, language="zh", model_size="small")
    
    step1_path = out_dir / "step1_asr.json"
    save_json(step1_result, step1_path)
    print(f"Saved: {step1_path}")
    
    if not step1_result["ok"]:
        print(f"Step1 FAILED: {step1_result['error_reason']}")
    else:
        transcript = step1_result["asr"]["transcript"]
        display_text = transcript[:80] + "..." if len(transcript) > 80 else transcript
        print(f"Transcript (first 80 chars): {display_text}")
    
    # ========== Step2: Pace/Pause ==========
    print("\n" + "=" * 50)
    print("Step2: Running Pace/Pause analysis...")
    step2_result = run_step2_pace_pause(
        audio_path=args.audio,
        asr_result=step1_result  # Pass for wpm/cpm calculation
    )
    
    step2_path = out_dir / "step2_pace_pause.json"
    save_json(step2_result, step2_path)
    print(f"Saved: {step2_path}")
    
    # Print Step2 summary
    pause_segments = step2_result.get("pause_segments", [])
    print(f"pause_segments count: {len(pause_segments)}")
    print(f"long_pause_count (>=1200ms): {step2_result['long_pause_count']}")
    print(f"max_pause_ms: {step2_result['max_pause_ms']}")
    print(f"wpm: {step2_result['wpm'] if step2_result['wpm'] is not None else 'null'}")
    print(f"speaking_rate_cpm: {step2_result['speaking_rate_cpm'] if step2_result['speaking_rate_cpm'] is not None else 'null'}")
    
    # ========== Step3: Text Features ==========
    print("\n" + "=" * 50)
    print("Step3: Running Text Features analysis...")
    step3_result = run_step3_text_features(
        step1_result=step1_result,
        step2_result=step2_result
    )
    
    step3_path = out_dir / "step3_text_features.json"
    save_json(step3_result, step3_path)
    print(f"Saved: {step3_path}")
    
    if not step3_result["ok"]:
        print(f"Step3 FAILED: {step3_result['error_reason']}")
    else:
        # Print Step3 summary
        tf = step3_result["text_features"]
        print(f"total_tokens: {tf['total_tokens']}")
        print(f"filler_count: {tf['filler_count']}")
        print(f"filler_ratio: {tf['filler_ratio'] if tf['filler_ratio'] is not None else 'null'}")
        print(f"repeat_ratio: {tf['repeat_ratio'] if tf['repeat_ratio'] is not None else 'null'}")
        print(f"ending_takeaway_present: {tf['ending_takeaway_present']}")
    
    # ========== Write Bundle ==========
    print("\n" + "=" * 50)
    print("Writing bundle...")
    
    bundle = {
        "step1": step1_result,
        "step2": step2_result,
        "step3": step3_result,
    }
    
    bundle_path = out_dir / "step1_2_3_bundle.json"
    save_json(bundle, bundle_path)
    print(f"Saved: {bundle_path}")
    
    # ========== Final Summary ==========
    print("\n" + "=" * 50)
    print("Pipeline Summary:")
    print(f"  Step1 ASR: {'OK' if step1_result['ok'] else 'FAILED'}")
    print(f"  Step2 Pace/Pause: OK")
    print(f"  Step3 Text Features: {'OK' if step3_result['ok'] else 'SKIPPED'}")
    print(f"\nAll artifacts saved to: {out_dir.absolute()}")


if __name__ == "__main__":
    main()
