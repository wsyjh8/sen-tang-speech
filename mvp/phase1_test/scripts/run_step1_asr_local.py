"""
CLI script to run Step1 ASR on local audio file.

Usage:
    python scripts/run_step1_asr_local.py --audio <path> [--out artifacts/step1_asr.json]

Output:
    - Prints ok/error_reason
    - Prints transcript (first 120 chars)
    - Prints segments count, first/last segment time
    - Generates 6-10s evidence_windows and prints first 2
    - Writes full JSON to --out
"""

import argparse
import json
from pathlib import Path

from app.asr.step1_asr import run_step1_asr, build_evidence_windows


def main():
    parser = argparse.ArgumentParser(description="Run Step1 ASR on local audio file")
    parser.add_argument("--audio", required=True, help="Path to local audio file")
    parser.add_argument(
        "--out",
        default="artifacts/step1_asr.json",
        help="Output JSON path (default: artifacts/step1_asr.json)"
    )
    parser.add_argument("--language", default="zh", help="Language code (default: zh)")
    parser.add_argument("--model", default="small", help="Whisper model size (default: small)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds (default: 120)")
    
    args = parser.parse_args()
    
    # Run ASR
    result = run_step1_asr(
        audio_path=args.audio,
        language=args.language,
        model_size=args.model,
        timeout_sec=args.timeout
    )
    
    # Print status
    print(f"ok: {result['ok']}")
    if result["error_reason"]:
        print(f"error_reason: {result['error_reason']}")
    
    asr = result["asr"]
    
    # Print transcript (first 120 chars)
    transcript = asr.get("transcript", "")
    if transcript:
        display_text = transcript[:120] + "..." if len(transcript) > 120 else transcript
        print(f"transcript (first 120 chars): {display_text}")
    else:
        print("transcript: (empty)")
    
    # Print segments info
    segments = asr.get("segments", [])
    print(f"segments count: {len(segments)}")
    if segments:
        first_seg = segments[0]
        last_seg = segments[-1]
        print(f"first segment: start_ms={first_seg['start_ms']}, end_ms={first_seg['end_ms']}")
        print(f"last segment: start_ms={last_seg['start_ms']}, end_ms={last_seg['end_ms']}")
    
    print(f"overall_confidence: {asr.get('overall_confidence', 0.0)}")
    
    # Build and print evidence windows
    evidence_windows = build_evidence_windows(segments)
    print(f"evidence_windows count: {len(evidence_windows)}")
    if evidence_windows:
        print("First 2 evidence windows:")
        for i, win in enumerate(evidence_windows[:2]):
            duration = win["end_ms"] - win["start_ms"]
            text_preview = win["text"][:60] + "..." if len(win["text"]) > 60 else win["text"]
            print(f"  [{i}] {win['start_ms']}ms - {win['end_ms']}ms ({duration}ms): {text_preview}")
    
    # Write output JSON
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nFull JSON written to: {out_path}")


if __name__ == "__main__":
    main()
