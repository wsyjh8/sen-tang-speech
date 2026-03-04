"""
FFmpeg audio transcoding utilities.

Transcodes uploaded audio files to 16kHz mono PCM16 WAV format
required by Step1 ASR and Step2 acoustic analysis.
"""

import shutil
import subprocess
from pathlib import Path


def transcode_to_16k_mono_wav(input_path: str | Path, output_path: str | Path) -> None:
    """
    Transcode audio file to 16kHz mono PCM16 WAV format.
    
    Args:
        input_path: Path to input audio file (webm, wav, ogg, mp3, etc.)
        output_path: Path to output WAV file
        
    Raises:
        FileNotFoundError: If ffmpeg is not installed or input file doesn't exist
        RuntimeError: If ffmpeg transcoding fails
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Check ffmpeg availability
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError(
            "ffmpeg not found; install or add to PATH. "
            "Download from https://ffmpeg.org/download.html"
        )
    
    # Check input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Build ffmpeg command
    # -ac 1: mono audio
    # -ar 16000: 16kHz sample rate
    # -c:a pcm_s16le: PCM 16-bit little-endian encoding
    # -y: overwrite output without asking
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", str(input_path),
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]
    
    # Run ffmpeg
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,  # 2 minute timeout
    )
    
    # Check result
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed with code {result.returncode}: {result.stderr}"
        )
    
    # Verify output file exists and has content
    if not output_path.exists():
        raise RuntimeError("ffmpeg completed but output file was not created")
    
    if output_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg completed but output file is empty")
