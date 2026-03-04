"""
VAD (Voice Activity Detection) using webrtcvad.

Lightweight, CPU-friendly VAD for MVP.
Supports 10/20/30ms frames. MVP uses 30ms.

Functions:
- load_wav_mono_16k(audio_path) -> (pcm_bytes, sample_rate=16000)
- frame_generator(pcm_bytes, sample_rate, frame_ms=30) -> iterator[bytes]
- vad_speech_flags(frames, sample_rate, aggressiveness=2) -> list[bool]
"""

import wave
from pathlib import Path
from typing import Iterator, Tuple, List, Optional

# Lazy import webrtcvad to handle missing dependency gracefully
_webrtcvad = None


def _get_webrtcvad():
    """Lazy load webrtcvad to handle missing dependency gracefully."""
    global _webrtcvad
    if _webrtcvad is None:
        try:
            import webrtcvad
            _webrtcvad = webrtcvad
        except ImportError:
            _webrtcvad = None
    return _webrtcvad


def load_wav_mono_16k(audio_path: str) -> Tuple[bytes, int]:
    """
    Load WAV file as mono 16kHz PCM.
    
    If input WAV is not 16k/mono, raises ValueError (MVP converges on this format).
    
    Args:
        audio_path: path to WAV file
    
    Returns:
        (pcm_bytes, sample_rate=16000)
    
    Raises:
        ValueError: if WAV is not 16kHz mono 16-bit
        FileNotFoundError: if file not found
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        
        # Validate format (MVP: 16kHz mono 16-bit)
        if framerate != 16000:
            raise ValueError(
                f"WAV sample rate is {framerate}Hz, expected 16000Hz. "
                "Please convert audio to 16kHz mono 16-bit first."
            )
        if channels != 1:
            raise ValueError(
                f"WAV has {channels} channel(s), expected 1 (mono). "
                "Please convert audio to 16kHz mono 16-bit first."
            )
        if sample_width != 2:
            raise ValueError(
                f"WAV sample width is {sample_width} bytes, expected 2 (16-bit). "
                "Please convert audio to 16kHz mono 16-bit first."
            )
        
        pcm_bytes = wf.readframes(wf.getnframes())
    
    return pcm_bytes, 16000


def frame_generator(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    frame_ms: int = 30
) -> Iterator[bytes]:
    """
    Generate frames from PCM bytes.
    
    webrtcvad supports 10/20/30ms frames. MVP uses 30ms.
    
    Args:
        pcm_bytes: raw PCM audio data (16-bit)
        sample_rate: sample rate (default 16000)
        frame_ms: frame duration in ms (default 30)
    
    Yields:
        frame bytes (each frame = frame_ms * sample_rate / 1000 * 2 bytes)
    """
    # Calculate frame size in bytes (16-bit = 2 bytes per sample)
    frame_size = int(sample_rate * frame_ms / 1000 * 2)
    
    offset = 0
    while offset + frame_size <= len(pcm_bytes):
        yield pcm_bytes[offset:offset + frame_size]
        offset += frame_size


def vad_speech_flags(
    frames: List[bytes],
    sample_rate: int = 16000,
    aggressiveness: int = 2
) -> List[bool]:
    """
    Run VAD on frames and return speech flags.
    
    Args:
        frames: list of frame bytes (each 30ms @ 16kHz)
        sample_rate: sample rate (default 16000)
        aggressiveness: 0-3, higher = more strict (default 2)
    
    Returns:
        list of bool: True if speech, False if silence
    
    Raises:
        RuntimeError: if webrtcvad not installed
    """
    webrtcvad = _get_webrtcvad()
    if webrtcvad is None:
        raise RuntimeError(
            "webrtcvad not installed. Run: pip install webrtcvad"
        )
    
    vad = webrtcvad.Vad(aggressiveness)
    
    flags = []
    for frame in frames:
        # Each frame must be 10/20/30ms @ 16kHz
        # 30ms @ 16kHz = 16000 * 0.03 * 2 = 960 bytes
        is_speech = vad.is_speech(frame, sample_rate)
        flags.append(is_speech)
    
    return flags


def detect_speech_regions(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    frame_ms: int = 30,
    aggressiveness: int = 2
) -> List[Tuple[int, int]]:
    """
    Detect speech regions in audio.
    
    Convenience function that combines frame_generator + vad_speech_flags.
    
    Args:
        pcm_bytes: raw PCM audio data
        sample_rate: sample rate (default 16000)
        frame_ms: frame duration in ms (default 30)
        aggressiveness: VAD aggressiveness 0-3 (default 2)
    
    Returns:
        list of (start_ms, end_ms) tuples for speech regions
    """
    frames = list(frame_generator(pcm_bytes, sample_rate, frame_ms))
    flags = vad_speech_flags(frames, sample_rate, aggressiveness)
    
    # Convert flags to regions
    regions = []
    in_speech = False
    start_ms = 0
    
    for i, is_speech in enumerate(flags):
        t_ms = i * frame_ms
        if is_speech and not in_speech:
            # Speech start
            in_speech = True
            start_ms = t_ms
        elif not is_speech and in_speech:
            # Speech end
            in_speech = False
            regions.append((start_ms, t_ms))
    
    # Handle speech continuing to end
    if in_speech:
        # Calculate audio duration
        duration_ms = len(frames) * frame_ms
        regions.append((start_ms, duration_ms))
    
    return regions
