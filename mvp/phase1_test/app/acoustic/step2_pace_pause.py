"""
Step2 Pace/Pause Analysis (MVP-0).

Input:
- audio_path: str
- (optional) asr_result: dict from Step1 (for wpm calculation)
  Note: Step2 pause/pace must run without ASR.

Output (pace_pause artifact):
{
  "pause_segments": [{"start_ms": int, "end_ms": int, "duration_ms": int}],
  "long_pause_count": int,          # pause >= 1200ms
  "max_pause_ms": int,
  "pace_series": [{"t_ms": int, "speech_ms": int}],  # per 1000ms bucket
  "wpm": float|null,                # only if transcript available
  "speaking_rate_cpm": float|null   # chars per minute; null if no transcript
}

Hard constraints:
1) long_pause_count threshold fixed at 1200ms
2) pace_series does NOT depend on transcript; only speech/silence from audio
3) wpm allowed null (must be null if ASR unavailable)
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from app.acoustic.vad_webrtc import (
    load_wav_mono_16k,
    frame_generator,
    vad_speech_flags,
)


def _speech_flags_to_pause_segments(
    flags: List[bool],
    frame_ms: int = 30
) -> List[Dict[str, int]]:
    """
    Convert speech flags to pause segments.
    
    Continuous non-speech frames form a pause_segment.
    start_ms/end_ms calculated from frame boundaries.
    duration_ms = end_ms - start_ms.
    
    Args:
        flags: list of bool (True=speech, False=silence)
        frame_ms: frame duration in ms (default 30)
    
    Returns:
        list of {"start_ms": int, "end_ms": int, "duration_ms": int}
    """
    if not flags:
        return []
    
    pause_segments = []
    in_pause = False
    start_ms = 0
    
    for i, is_speech in enumerate(flags):
        t_ms = i * frame_ms
        if not is_speech and not in_pause:
            # Pause start
            in_pause = True
            start_ms = t_ms
        elif is_speech and in_pause:
            # Pause end
            in_pause = False
            pause_segments.append({
                "start_ms": start_ms,
                "end_ms": t_ms,
                "duration_ms": t_ms - start_ms,
            })
    
    # Handle pause continuing to end
    if in_pause:
        duration_ms = len(flags) * frame_ms
        pause_segments.append({
            "start_ms": start_ms,
            "end_ms": duration_ms,
            "duration_ms": duration_ms - start_ms,
        })
    
    return pause_segments


def _compute_pace_series(
    flags: List[bool],
    frame_ms: int = 30,
    bucket_ms: int = 1000
) -> List[Dict[str, int]]:
    """
    Compute pace series: speech ms per bucket.
    
    Args:
        flags: list of bool (True=speech, False=silence)
        frame_ms: frame duration in ms (default 30)
        bucket_ms: bucket size in ms (default 1000)
    
    Returns:
        list of {"t_ms": int, "speech_ms": int}
    """
    if not flags:
        return []
    
    total_duration_ms = len(flags) * frame_ms
    pace_series = []
    
    # Iterate over buckets
    t_ms = 0
    while t_ms < total_duration_ms:
        bucket_end = t_ms + bucket_ms
        
        # Count speech frames in this bucket
        speech_ms = 0
        for i, is_speech in enumerate(flags):
            frame_start = i * frame_ms
            frame_end = frame_start + frame_ms
            
            # Check if frame overlaps with bucket
            if frame_start < bucket_end and frame_end > t_ms:
                if is_speech:
                    # Calculate overlap
                    overlap_start = max(frame_start, t_ms)
                    overlap_end = min(frame_end, bucket_end)
                    speech_ms += overlap_end - overlap_start
        
        pace_series.append({
            "t_ms": t_ms,
            "speech_ms": speech_ms,
        })
        
        t_ms = bucket_end
    
    return pace_series


def _compute_wpm(asr_result: Optional[Dict], audio_duration_ms: float) -> Optional[float]:
    r"""
    Compute words per minute from ASR transcript.
    
    Tokenization: simple split on whitespace/punctuation for Chinese.
    Note: Python re doesn't support \p{P}, so we use a simpler pattern.
    
    Args:
        asr_result: Step1 output dict with asr.transcript
        audio_duration_ms: audio duration in ms
    
    Returns:
        wpm (float) or None if transcript unavailable
    """
    if asr_result is None:
        return None
    
    asr = asr_result.get("asr", {})
    transcript = asr.get("transcript", "")
    
    if not transcript or not transcript.strip():
        return None
    
    # Simple tokenization: split on whitespace
    # For Chinese with spaces between words, this counts words
    # If no spaces, count as single token (Chinese typically doesn't use spaces)
    tokens = transcript.strip().split()
    tokens = [t for t in tokens if t.strip()]
    token_count = len(tokens)
    
    if token_count == 0:
        return None
    
    duration_min = audio_duration_ms / 60000.0
    if duration_min <= 0:
        return None
    
    wpm = token_count / duration_min
    return round(wpm, 2)


def _compute_cpm(asr_result: Optional[Dict], audio_duration_ms: float) -> Optional[float]:
    """
    Compute characters per minute from ASR transcript.
    
    Args:
        asr_result: Step1 output dict with asr.transcript
        audio_duration_ms: audio duration in ms
    
    Returns:
        cpm (float) or None if transcript unavailable
    """
    if asr_result is None:
        return None
    
    asr = asr_result.get("asr", {})
    transcript = asr.get("transcript", "")
    
    if not transcript:
        return None
    
    # Count non-whitespace characters
    chars_count = len(transcript.replace(" ", "").replace("\n", ""))
    
    if chars_count == 0:
        return None
    
    duration_min = audio_duration_ms / 60000.0
    if duration_min <= 0:
        return None
    
    cpm = chars_count / duration_min
    return round(cpm, 2)


def run_step2_pace_pause(
    audio_path: str,
    asr_result: Optional[Dict] = None,
    frame_ms: int = 30,
    bucket_ms: int = 1000,
    long_pause_ms: int = 1200
) -> Dict[str, Any]:
    """
    Run Step2 Pace/Pause analysis.
    
    Args:
        audio_path: path to local audio file (WAV 16kHz mono 16-bit)
        asr_result: optional Step1 output dict (for wpm/cpm calculation)
        frame_ms: VAD frame duration in ms (default 30)
        bucket_ms: pace series bucket size in ms (default 1000)
        long_pause_ms: threshold for long pause in ms (default 1200)
    
    Returns:
        {
          "pause_segments": [...],
          "long_pause_count": int,
          "max_pause_ms": int,
          "pace_series": [...],
          "wpm": float|null,
          "speaking_rate_cpm": float|null
        }
    """
    # Load audio
    pcm_bytes, sample_rate = load_wav_mono_16k(audio_path)
    
    # Calculate audio duration
    # 16-bit = 2 bytes per sample
    num_samples = len(pcm_bytes) // 2
    audio_duration_ms = int(num_samples / sample_rate * 1000)
    
    # Generate frames and run VAD
    frames = list(frame_generator(pcm_bytes, sample_rate, frame_ms))
    flags = vad_speech_flags(frames, sample_rate, aggressiveness=2)
    
    # Convert to pause segments
    pause_segments = _speech_flags_to_pause_segments(flags, frame_ms)
    
    # Calculate long_pause_count (>= 1200ms)
    long_pause_count = sum(
        1 for seg in pause_segments if seg["duration_ms"] >= long_pause_ms
    )
    
    # Calculate max_pause_ms
    max_pause_ms = max(
        (seg["duration_ms"] for seg in pause_segments),
        default=0
    )
    
    # Calculate pace series
    pace_series = _compute_pace_series(flags, frame_ms, bucket_ms)
    
    # Calculate wpm and cpm
    wpm = _compute_wpm(asr_result, audio_duration_ms)
    cpm = _compute_cpm(asr_result, audio_duration_ms)
    
    return {
        "pause_segments": pause_segments,
        "long_pause_count": long_pause_count,
        "max_pause_ms": max_pause_ms,
        "pace_series": pace_series,
        "wpm": wpm,
        "speaking_rate_cpm": cpm,
    }
