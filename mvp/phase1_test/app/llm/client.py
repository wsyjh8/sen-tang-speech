"""LLM client with retry, backoff, and fallback support."""

import os
import random
import time
import uuid
from typing import Any

from app.llm.prm_v0_1 import (
    PRIMARY_MODEL, BACKUP_MODEL,
    TEMPERATURE, TOP_P, MAX_TOKENS, TIMEOUT_SEC,
    RETRY_TIMEOUT, RETRY_429, RETRY_5XX,
    BACKOFF_BASE, BACKOFF_JITTER,
    compute_hash
)


class LLMClientError(Exception):
    """LLM client error."""
    pass


class LLMUnavailableError(LLMClientError):
    """LLM service unavailable. Carries trace_fields for logging."""
    def __init__(self, message: str, trace_fields: dict):
        super().__init__(message)
        self.trace_fields = trace_fields


def _get_api_config() -> tuple[str | None, str | None]:
    """Get API base_url and key from environment.
    
    Tries QWEN_* env vars first (for live testing), then falls back to LLM_* vars.
    """
    # Try QWEN_* env vars first (for live testing)
    base_url = os.environ.get("QWEN_BASE_URL") or os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("LLM_API_KEY")
    return base_url, api_key


def _get_model_config() -> tuple[str, str]:
    """Get model configuration from environment."""
    primary = os.environ.get("QWEN_MODEL_PRIMARY", PRIMARY_MODEL)
    backup = os.environ.get("QWEN_MODEL_BACKUP", BACKUP_MODEL)
    return primary, backup


def _compute_backoff(attempt: int) -> float:
    """Compute backoff with jitter."""
    base = BACKOFF_BASE * (2 ** attempt)
    jitter = random.uniform(0, BACKOFF_JITTER)
    return base + jitter


def _should_retry(status_code: int | None, retry_count: int, error_type: str) -> bool:
    """Determine if request should be retried."""
    if error_type == "timeout":
        return retry_count < RETRY_TIMEOUT
    elif error_type == "http_429":
        return retry_count < RETRY_429
    elif error_type == "http_5xx":
        return retry_count < RETRY_5XX
    return False


def call_llm(
    messages: list[dict],
    request_id: str | None = None
) -> tuple[str | None, dict]:
    """
    Call LLM with retry and backoff.

    Args:
        messages: List of message dicts for the API.
        request_id: Optional request ID for tracing.

    Returns:
        (response_text, trace_fields)
        response_text is the LLM response content if successful.
        trace_fields contains metadata for logging.

    Raises:
        LLMUnavailableError: If API key not configured or all retries failed.
                             Carries trace_fields in the exception.
    """
    request_id = request_id or str(uuid.uuid4())
    base_url, api_key = _get_api_config()
    primary_model, backup_model = _get_model_config()

    trace_fields = {
        "request_id": request_id,
        "model": primary_model,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "timeout_sec": TIMEOUT_SEC,
        "retry_count": 0,
        "prompt_hash": compute_hash(str(messages)),
        "input_hash": compute_hash(str(messages)[:500]),
    }

    # Check if API is configured
    if not api_key:
        trace_fields["fallback_reason"] = "CALL_FAILED:API_KEY_NOT_CONFIGURED"
        trace_fields["output_hash"] = ""
        trace_fields["latency_ms"] = 0
        raise LLMUnavailableError("API_KEY_NOT_CONFIGURED", trace_fields)

    if not base_url:
        trace_fields["fallback_reason"] = "CALL_FAILED:BASE_URL_NOT_CONFIGURED"
        trace_fields["output_hash"] = ""
        trace_fields["latency_ms"] = 0
        raise LLMUnavailableError("BASE_URL_NOT_CONFIGURED", trace_fields)

    # Try primary model first, then backup
    import httpx
    
    for model in [primary_model, backup_model]:
        trace_fields["model"] = model
        retry_count = 0
        last_error = None
        last_error_type = None

        while True:
            try:
                # Real API call
                with httpx.Client() as client:
                    response = client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": TEMPERATURE,
                            "top_p": TOP_P,
                            "max_tokens": MAX_TOKENS,
                        },
                        timeout=TIMEOUT_SEC
                    )
                    response.raise_for_status()
                    data = response.json()
                    response_text = data["choices"][0]["message"]["content"]
                    trace_fields["output_hash"] = compute_hash(response_text)
                    trace_fields["latency_ms"] = int(response.elapsed.total_seconds() * 1000)
                    return response_text, trace_fields

            except httpx.TimeoutException as e:
                last_error = e
                last_error_type = "timeout"
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    last_error_type = "http_429"
                elif 500 <= e.response.status_code < 600:
                    last_error_type = "http_5xx"
                else:
                    last_error_type = "http_error"
            except Exception as e:
                last_error = e
                last_error_type = "unknown"

            retry_count += 1
            trace_fields["retry_count"] = retry_count

            if not _should_retry(None, retry_count, last_error_type):
                break

            backoff = _compute_backoff(retry_count - 1)
            time.sleep(backoff)

        # If primary failed, try backup once
        if model == primary_model:
            trace_fields["fallback_reason"] = f"primary_failed_{last_error_type}"
            continue
        else:
            trace_fields["fallback_reason"] = f"backup_failed_{last_error_type}"

    # All retries exhausted
    trace_fields["fallback_reason"] = "CALL_FAILED:ALL_RETRIES_EXHAUSTED"
    trace_fields["output_hash"] = ""
    trace_fields["latency_ms"] = 0
    raise LLMUnavailableError("ALL_RETRIES_EXHAUSTED", trace_fields)


def parse_llm_response(response_text: str) -> Any:
    """
    Parse LLM response JSON.
    
    Args:
        response_text: Raw response text from LLM.
    
    Returns:
        Parsed JSON data.
    
    Raises:
        ValueError: If JSON is invalid.
    """
    import json
    return json.loads(response_text)
