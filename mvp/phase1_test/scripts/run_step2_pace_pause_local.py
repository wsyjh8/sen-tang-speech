"""
CLI script to run Step2 Pace/Pause analysis on local audio file.

Usage:
    python scripts/run_step2_pace_pause_local.py --audio <path> [--asr_json <path>] [--out artifacts/step2_pace_pause.json]

Output:
    - Prints pause_segments count
    - Prints long_pause_count, max_pause_ms
    - Prints first 5 pace_series buckets
    - Prints wpm and speaking_rate_cpm (null if asr_json not provided)
    - Writes full JSON to --out
"""

import argparse
import json
from pathlib import Path

from app.acoustic.step2_pace_pause import run_step2_pace_pause


def main():
    parser = argparse.ArgumentParser(description="Run Step2 Pace/Pause analysis on local audio file")
    parser.add_argument("--audio", required=True, help="Path to local audio file (WAV 16kHz mono 16-bit)")
    parser.add_argument(
        "--asr_json",
        default=None,
        help="Path to Step1 ASR JSON output (optional, for wpm/cpm calculation)"
    )
    parser.add_argument(
        "--out",
        default="artifacts/step2_pace_pause.json",
        help="Output JSON path (default: artifacts/step2_pace_pause.json)"
    )
    
    args = parser.parse_args()
    
    # Load ASR result if provided
    asr_result = None
    if args.asr_json:
        asr_path = Path(args.asr_json)
        if asr_path.exists():
            with open(asr_path, "r", encoding="utf-8") as f:
                asr_result = json.load(f)
            print(f"Loaded ASR result from: {asr_path}")
        else:
            print(f"Warning: ASR JSON not found: {asr_path}")
    
    # Run Step2
    result = run_step2_pace_pause(
        audio_path=args.audio,
        asr_result=asr_result
    )
    
    # Print results
    pause_segments = result.get("pause_segments", [])
    print(f"pause_segments count: {len(pause_segments)}")
    print(f"long_pause_count (>=1200ms): {result['long_pause_count']}")
    print(f"max_pause_ms: {result['max_pause_ms']}")
    
    # Print first 5 pace_series buckets
    pace_series = result.get("pace_series", [])
    print(f"pace_series count: {len(pace_series)}")
    print("First 5 pace_series buckets:")
    for i, bucket in enumerate(pace_series[:5]):
        print(f"  [{i}] t_ms={bucket['t_ms']}, speech_ms={bucket['speech_ms']}")
    
    # Print wpm and cpm
    wpm = result.get("wpm")
    cpm = result.get("speaking_rate_cpm")
    print(f"wpm: {wpm if wpm is not None else 'null'}")
    print(f"speaking_rate_cpm: {cpm if cpm is not None else 'null'}")
    
    # Write output JSON
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nFull JSON written to: {out_path}")


if __name__ == "__main__":
    main()
