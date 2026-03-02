#!/usr/bin/env python3
"""Debug script to test LLM call and print raw response."""

import os
import sys
import json

from app.llm.prm_v0_1 import build_messages
from app.llm.client import call_llm, parse_llm_response


def main() -> int:
    api_key = os.environ.get("QWEN_API_KEY")
    base_url = os.environ.get("QWEN_BASE_URL")
    
    if not api_key or not base_url:
        print("ERROR: QWEN_API_KEY or QWEN_BASE_URL not set")
        print("Please set:")
        print("  set QWEN_API_KEY=your-key")
        print("  set QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1")
        return 1
    
    print(f"API Key: {'***' + api_key[-4:]}")
    print(f"Base URL: {base_url}")
    
    # Build test messages
    messages = build_messages(
        pol_version="POL-v0.1",
        top_trigger_id="BR-OPP-001-R-TASK-001",
        top_trigger_evidence={
            "time_ranges": [{"start_ms": 0, "end_ms": 1000}],
            "text_snippets": ["我觉得这个事情的核心结论是……"]
        },
        transcript_snippets="我觉得这个事情的核心结论是……"
    )
    
    print("\n=== Request Messages ===")
    print(json.dumps(messages, indent=2, ensure_ascii=False))
    
    try:
        # Call LLM
        print("\n=== Calling LLM ===")
        response_text, trace_fields = call_llm(messages)
        
        print(f"Model used: {trace_fields.get('model')}")
        print(f"Retry count: {trace_fields.get('retry_count')}")
        print(f"Latency: {trace_fields.get('latency_ms')}ms")
        
        print("\n=== Raw Response ===")
        print(response_text)
        
        # Try to parse
        print("\n=== Parsing JSON ===")
        data = parse_llm_response(response_text)
        print("JSON parsing: SUCCESS")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        
        return 0
        
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
