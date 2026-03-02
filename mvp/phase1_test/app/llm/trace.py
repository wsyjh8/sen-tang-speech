"""Trace logging for LLM requests."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def get_trace_file() -> Path:
    """Get path to trace file."""
    base_dir = Path(__file__).parent.parent.parent / "artifacts"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "llm_trace.jsonl"


def write_trace(event: dict) -> None:
    """
    Append trace event to JSONL file.
    
    Args:
        event: Dict containing trace fields:
            - request_id, prm_version, pol_version
            - model, temperature, top_p, max_tokens, timeout_sec
            - retry_count, prompt_hash, input_hash, output_hash
            - latency_ms, fallback_reason
    """
    trace_file = get_trace_file()
    
    # Add timestamp
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Write as JSONL
    with open(trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
