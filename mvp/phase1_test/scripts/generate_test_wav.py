"""Generate a test WAV file (16kHz mono 16-bit) for testing."""

import wave
import struct
import math

def generate_test_wav(output_path: str, duration_sec: float = 5.0):
    """
    Generate a test WAV file with a sine wave tone.
    
    Args:
        output_path: path to output WAV file
        duration_sec: duration in seconds (default 5.0)
    """
    sample_rate = 16000
    frequency = 440  # A4 tone
    
    num_samples = int(sample_rate * duration_sec)
    
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Generate sine wave
            t = i / sample_rate
            value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
            wf.writeframes(struct.pack("<h", value))
    
    print(f"Generated test WAV: {output_path}")
    print(f"  Duration: {duration_sec}s")
    print(f"  Sample rate: {sample_rate}Hz")
    print(f"  Channels: 1 (mono)")
    print(f"  Sample width: 16-bit")


if __name__ == "__main__":
    from pathlib import Path
    
    # Output to artifacts directory (sibling of scripts/)
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = artifacts_dir / "test_16k.wav"
    generate_test_wav(str(output_path), duration_sec=5.0)
