"""PRM-v0.1 - Prompt construction and versioning."""

import hashlib
import json

from app.llm.prompts.prompt_top5_v0_1 import SYSTEM_PROMPT, TASK_PROMPT

PRM_VERSION = "PRM-v0.1"

# Frozen model parameters
PRIMARY_MODEL = "qwen-plus"
BACKUP_MODEL = "qwen-turbo"
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 800
TIMEOUT_SEC = 20

# Token budget guardrails
INPUT_TOKENS_CAP = 1700
OUTPUT_TOKENS_CAP = 800
TOTAL_TOKENS_CAP = 2500
TRANSCRIPT_SNIPPETS_MAX_CHARS = 1200

# Retry configuration
RETRY_TIMEOUT = 1
RETRY_429 = 2
RETRY_5XX = 2
BACKOFF_BASE = 1.0  # seconds
BACKOFF_JITTER = 0.2  # 200ms

# Concurrency limit
MAX_IN_FLIGHT = 2


def compute_hash(text: str) -> str:
    """Compute SHA256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_messages(
    pol_version: str,
    top_trigger_id: str | None,
    top_trigger_evidence: dict | None,
    transcript_snippets: str,
    metrics: dict | None = None
) -> list[dict]:
    """
    Build messages for LLM request using Top5 prompt.

    Args:
        pol_version: POL version string
        top_trigger_id: The top trigger rule id
        top_trigger_evidence: Evidence from top trigger
        transcript_snippets: Redacted transcript snippets (<=1200 chars)
        metrics: Optional dict with wpm/filler_ratio/repeat_ratio/long_pause_count/max_pause_ms

    Returns:
        List of message dicts with system and user roles.
    """
    system_message = {
        "role": "system",
        "content": SYSTEM_PROMPT
    }

    # Extract metrics
    metrics = metrics or {}
    wpm = metrics.get("wpm")
    filler_ratio = metrics.get("filler_ratio")
    repeat_ratio = metrics.get("repeat_ratio")
    long_pause_count = metrics.get("long_pause_count")
    max_pause_ms = metrics.get("max_pause_ms")

    # Build user message using TASK_PROMPT
    user_content = TASK_PROMPT.format(
        pol_version=pol_version,
        top_trigger_id=top_trigger_id,
        wpm=wpm,
        filler_ratio=filler_ratio,
        repeat_ratio=repeat_ratio,
        long_pause_count=long_pause_count,
        max_pause_ms=max_pause_ms
    )

    # Add transcript snippets
    user_content += f"\n\nTranscript Snippets:\n{transcript_snippets}"

    # Add evidence if available
    if top_trigger_evidence:
        time_ranges = top_trigger_evidence.get("time_ranges", [])
        text_snippets = top_trigger_evidence.get("text_snippets", [])
        if time_ranges or text_snippets:
            user_content += f"\n\nEvidence:\n- Time ranges: {time_ranges}\n- Snippets: {text_snippets}"

    user_message = {
        "role": "user",
        "content": user_content
    }

    return [system_message, user_message]


def compute_prompt_hash(messages: list[dict]) -> str:
    """Compute hash of messages for trace."""
    messages_json = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return compute_hash(messages_json)
