"""LLM prompts package."""

from app.llm.prompts.prompt_top5_v0_1 import (
    SYSTEM_PROMPT,
    TASK_PROMPT,
    OUTPUT_SCHEMA,
    ALLOWED_DRILL_IDS,
    DEFAULT_DRILL_ID,
)

__all__ = [
    "SYSTEM_PROMPT",
    "TASK_PROMPT",
    "OUTPUT_SCHEMA",
    "ALLOWED_DRILL_IDS",
    "DEFAULT_DRILL_ID",
]
