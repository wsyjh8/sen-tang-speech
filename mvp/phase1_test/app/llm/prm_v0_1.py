"""PRM-v0.1 - Prompt construction and versioning."""

import hashlib
import json

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
    transcript_snippets: str
) -> list[dict]:
    """
    Build messages for LLM request.
    
    Args:
        pol_version: POL version string
        top_trigger_id: The top trigger rule id
        top_trigger_evidence: Evidence from top trigger
        transcript_snippets: Redacted transcript snippets (<=1200 chars)
    
    Returns:
        List of message dicts with system and user roles.
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a speech coaching assistant. "
            "Generate exactly ONE actionable suggestion based on the triggered rule and evidence. "
            "Output must be valid JSON with this exact structure:\n"
            "{\n"
            '  "suggestions": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "problem": "string",\n'
            '      "cause": "string",\n'
            '      "evidence_ref": {\n'
            '        "time_ranges": [{"start_ms": int, "end_ms": int}],\n'
            '        "text_snippets": ["string"]\n'
            "      },\n"
            '      "drill": {\n'
            '        "drill_id": "string",\n'
            '        "steps": ["string"],\n'
            '        "duration_sec": int,\n'
            '        "tips": ["string"]\n'
            "      },\n"
            '      "acceptance": {\n'
            '        "metric": "string",\n'
            '        "target": "string|number",\n'
            '        "how_to_measure": "string"\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- suggestions must be an array with 1-3 items\n"
            "- All fields are required\n"
            "- evidence_ref must copy from provided evidence (no fabrication)\n"
            "- drill_id must be from allowlist: SILENCE_REPLACE, PRESET_OPENERS, REPLACEMENT_BANK, SLOW_10_PERCENT, ONE_LINE_TAKEAWAY\n"
        )
    }
    
    evidence_context = ""
    if top_trigger_evidence:
        time_ranges = top_trigger_evidence.get("time_ranges", [])
        text_snippets = top_trigger_evidence.get("text_snippets", [])
        if time_ranges or text_snippets:
            evidence_context = f"\nEvidence:\n- Time ranges: {time_ranges}\n- Snippets: {text_snippets}"
    
    user_message = {
        "role": "user",
        "content": (
            f"POL Version: {pol_version}\n"
            f"Triggered Rule: {top_trigger_id}\n"
            f"Transcript Snippets:\n{transcript_snippets}"
            f"{evidence_context}\n"
            "\nGenerate ONE suggestion to address this issue."
        )
    }
    
    return [system_message, user_message]


def compute_prompt_hash(messages: list[dict]) -> str:
    """Compute hash of messages for trace."""
    messages_json = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return compute_hash(messages_json)
