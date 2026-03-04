"""Acoustic module for Step2 pace/pause analysis."""

from app.acoustic.vad_webrtc import (
    load_wav_mono_16k,
    frame_generator,
    vad_speech_flags,
    detect_speech_regions,
)
from app.acoustic.step2_pace_pause import (
    run_step2_pace_pause,
    _speech_flags_to_pause_segments,
    _compute_pace_series,
    _compute_wpm,
    _compute_cpm,
)

__all__ = [
    "load_wav_mono_16k",
    "frame_generator",
    "vad_speech_flags",
    "detect_speech_regions",
    "run_step2_pace_pause",
    "_speech_flags_to_pause_segments",
    "_compute_pace_series",
    "_compute_wpm",
    "_compute_cpm",
]
