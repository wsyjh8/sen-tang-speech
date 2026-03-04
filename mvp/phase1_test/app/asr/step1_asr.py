"""
Step1 ASR: Local CPU faster-whisper implementation.

Input: local audio file
Output: asr artifact (dict/JSON) with frozen structure:
{
  "transcript": str,
  "segments": [
    {"start_ms": int, "end_ms": int, "text": str, "confidence": float}
  ],
  "overall_confidence": float  # 0..1
}

Hard constraints:
- segments must be monotonically increasing in time (no reverse order)
- start_ms/end_ms in milliseconds as int
- Coverage: first segment start_ms=0, last segment end_ms≈duration_ms
- Evidence baseline: generate 6-10s window candidates from segments
- ASR failure must return degradable result (no crash)
"""

import subprocess
import wave
from pathlib import Path
from typing import Optional

# Lazy import faster_whisper to avoid hard dependency error at import time
_faster_whisper = None


def _get_faster_whisper():
    """Lazy load faster_whisper to handle missing dependency gracefully."""
    global _faster_whisper
    if _faster_whisper is None:
        try:
            from faster_whisper import WhisperModel
            _faster_whisper = WhisperModel
        except ImportError:
            _faster_whisper = None
    return _faster_whisper


def _get_audio_duration_ms(audio_path: str) -> Optional[int]:
    """
    Get audio duration in milliseconds.
    
    Supports WAV via standard library wave.
    For non-WAV, tries ffprobe via subprocess, returns None if fails.
    
    Returns:
        duration in ms, or None if cannot determine
    """
    path = Path(audio_path)
    suffix = path.suffix.lower()
    
    if suffix == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    duration_sec = frames / rate
                    return int(duration_sec * 1000)
        except Exception:
            pass
        return None
    
    # Try ffprobe for non-WAV
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(path)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            return int(duration * 1000)
    except Exception:
        pass
    
    return None


def _compute_confidence(segment_obj: dict) -> float:
    """
    Compute confidence for a segment.
    
    If faster-whisper provides no_speech_prob, use 1 - no_speech_prob (clipped to 0..1).
    Otherwise default to 0.8.
    
    Args:
        segment_obj: segment dict that may contain 'no_speech_prob' or 'confidence'
    
    Returns:
        confidence value in range 0..1
    """
    if "no_speech_prob" in segment_obj:
        conf = 1.0 - segment_obj["no_speech_prob"]
        return max(0.0, min(1.0, conf))
    elif "confidence" in segment_obj:
        conf = segment_obj["confidence"]
        return max(0.0, min(1.0, conf))
    else:
        return 0.8


def _validate_and_fix_segments(segments: list, duration_ms: Optional[int]) -> list:
    """
    Validate and fix segments.
    
    - Convert seconds to ms, cast to int
    - Validate monotonic increasing: if reverse order found, raise ValueError
    - If duration_ms available: force segments[0].start_ms=0, segments[-1].end_ms=duration_ms
    
    Args:
        segments: raw segments from ASR
        duration_ms: audio duration in ms, or None
    
    Returns:
        validated and fixed segments list
    
    Raises:
        ValueError: if segments are not monotonically increasing
    """
    if not segments:
        return []
    
    fixed = []
    for seg in segments:
        fixed_seg = {
            "start_ms": int(seg["start"] * 1000) if isinstance(seg["start"], float) else int(seg["start"]),
            "end_ms": int(seg["end"] * 1000) if isinstance(seg["end"], float) else int(seg["end"]),
            "text": str(seg.get("text", "")),
            "confidence": _compute_confidence(seg),
        }
        fixed.append(fixed_seg)
    
    # Validate monotonic increasing
    for i in range(1, len(fixed)):
        if fixed[i]["start_ms"] < fixed[i - 1]["end_ms"]:
            # Overlap is okay, but check for reverse order
            pass
        if fixed[i]["start_ms"] < fixed[i - 1]["start_ms"]:
            raise ValueError(
                f"Segments not monotonically increasing: "
                f"segment[{i-1}].start_ms={fixed[i-1]['start_ms']} > "
                f"segment[{i}].start_ms={fixed[i]['start_ms']}"
            )
    
    # Apply coverage fix if duration_ms available
    if duration_ms is not None and len(fixed) > 0:
        fixed[0]["start_ms"] = 0
        fixed[-1]["end_ms"] = duration_ms
    
    return fixed


def build_evidence_windows(segments: list, min_ms: int = 6000, max_ms: int = 10000) -> list:
    """
    Build evidence windows from segments (6-10s baseline).
    
    Rule: concatenate segments text in order, create a window when reaching 6-10s.
    Last window is allowed to be <6s only if total remaining duration is insufficient.
    
    Args:
        segments: validated segments list
        min_ms: minimum window duration (default 6000ms)
        max_ms: maximum window duration (default 10000ms)
    
    Returns:
        list of {"start_ms": int, "end_ms": int, "text": str}
    """
    if not segments:
        return []
    
    windows = []
    current_start = None
    current_text = ""
    current_end = None
    
    for seg in segments:
        if current_start is None:
            current_start = seg["start_ms"]
            current_end = seg["end_ms"]
            current_text = seg["text"]
        else:
            # Check if adding this segment exceeds max_ms
            potential_duration = seg["end_ms"] - current_start
            if potential_duration > max_ms and current_end - current_start >= min_ms:
                # Flush current window
                windows.append({
                    "start_ms": current_start,
                    "end_ms": current_end,
                    "text": current_text,
                })
                # Start new window
                current_start = seg["start_ms"]
                current_end = seg["end_ms"]
                current_text = seg["text"]
            else:
                # Extend current window
                current_end = seg["end_ms"]
                current_text = current_text + " " + seg["text"] if current_text else seg["text"]
    
    # Flush last window (allowed to be <min_ms if total remaining is insufficient)
    if current_start is not None:
        windows.append({
            "start_ms": current_start,
            "end_ms": current_end,
            "text": current_text,
        })
    
    return windows


def run_step1_asr(
    audio_path: str,
    language: str = "zh",
    model_size: str = "small",
    timeout_sec: int = 120
) -> dict:
    """
    Run Step1 ASR using faster-whisper (local CPU).
    
    Args:
        audio_path: path to local audio file
        language: language code (default "zh" for Chinese)
        model_size: whisper model size (default "small")
        timeout_sec: timeout in seconds (default 120)
    
    Returns:
        {
          "ok": bool,
          "error_reason": str|None,
          "asr": {
            "transcript": str,
            "segments": [...],
            "overall_confidence": float
          }
        }
    
    If ok=False: asr.transcript="", asr.segments=[], asr.overall_confidence=0.0
    """
    def make_fail(error_reason: str) -> dict:
        return {
            "ok": False,
            "error_reason": error_reason,
            "asr": {
                "transcript": "",
                "segments": [],
                "overall_confidence": 0.0,
            }
        }
    
    # Check file exists
    if not Path(audio_path).exists():
        return make_fail(f"Audio file not found: {audio_path}")
    
    # Get duration (optional, for validation)
    duration_ms = _get_audio_duration_ms(audio_path)
    
    # Load faster-whisper
    WhisperModel = _get_faster_whisper()
    if WhisperModel is None:
        return make_fail("faster-whisper not installed. Run: pip install faster-whisper")
    
    try:
        # Load model (CPU mode)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception as e:
        return make_fail(f"Failed to load whisper model: {e}")
    
    try:
        # Run transcription
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=False,
        )
        
        # Collect segments
        raw_segments = []
        for seg in segments_iter:
            raw_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "no_speech_prob": getattr(seg, "no_speech_prob", None),
            })
        
        # Validate and fix segments
        try:
            validated_segments = _validate_and_fix_segments(raw_segments, duration_ms)
        except ValueError as e:
            return make_fail(f"Segment validation failed: {e}")
        
        # Build transcript
        transcript = " ".join(seg["text"] for seg in validated_segments if seg["text"])
        
        # Compute overall confidence
        if validated_segments:
            overall_confidence = sum(seg["confidence"] for seg in validated_segments) / len(validated_segments)
        else:
            overall_confidence = 0.0
        
        return {
            "ok": True,
            "error_reason": None,
            "asr": {
                "transcript": transcript,
                "segments": validated_segments,
                "overall_confidence": round(overall_confidence, 4),
            }
        }
        
    except Exception as e:
        return make_fail(f"ASR transcription failed: {e}")
