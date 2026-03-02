"""FastAPI application with /health, /mock/report, and /pipeline/step4_demo endpoints."""

import json
from pathlib import Path

from fastapi import FastAPI

from app.mock_report import build_mock_report
from app.pipeline.step4_rule_engine import step4_rule_engine
from app.pipeline.step5_llm_feedback import step5_llm_feedback

app = FastAPI()


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/mock/report")
def mock_report() -> dict:
    """Generate and return a mock ReportResponse using default case1 data."""
    report = build_mock_report()

    # Ensure artifacts directory exists
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write to artifacts/mock_report.json
    output_path = artifacts_dir / "mock_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"mock report generated path={output_path}")

    return report


@app.get("/pipeline/step4_demo")
def pipeline_step4_demo() -> dict:
    """
    Step4 Integration Demo endpoint.
    
    Constructs a fixed triggered_triggers (3+ rules covering weight flip & tie-break),
    calls step4_rule_engine, writes to artifacts/step4_demo_report.json, and returns report.
    """
    # Fixed demo data: 3 triggers covering weight flip & tie-break scenarios
    demo_triggered_triggers = [
        {
            "id": "demo_base",
            "impact_score": 0.6,
            "severity": "P1",
            "conflict_priority": 2,
            "trigger_count": 3,
            "evidence": {
                "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                "text_snippets": ["demo base rule snippet"],
            },
        },
        {
            "id": "demo_boosted",
            "impact_score": 0.5,
            "severity": "P2",
            "conflict_priority": 3,
            "trigger_count": 2,
            "evidence": {
                "time_ranges": [{"start_ms": 6000, "end_ms": 10000}],
                "text_snippets": ["demo boosted rule snippet 1", "demo boosted rule snippet 2"],
            },
        },
        {
            "id": "demo_tie_a",
            "impact_score": 0.4,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 5,
            "evidence": {
                "time_ranges": [{"start_ms": 11000, "end_ms": 15000}],
                "text_snippets": ["demo tie-break A"],
            },
        },
        {
            "id": "demo_tie_b",
            "impact_score": 0.4,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 3,
            "evidence": {
                "time_ranges": [{"start_ms": 16000, "end_ms": 20000}],
                "text_snippets": ["demo tie-break B"],
            },
        },
    ]
    
    # Weight override to demonstrate flip
    demo_pack_weights = {"demo_boosted": 2.5}
    
    # Call Step4 integration layer
    report = step4_rule_engine(demo_triggered_triggers, demo_pack_weights)
    
    # Ensure artifacts directory exists
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to artifacts/step4_demo_report.json
    output_path = artifacts_dir / "step4_demo_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"step4 demo report generated path={output_path}")

    return report


@app.get("/pipeline/step5_demo")
def pipeline_step5_demo() -> dict:
    """
    Step5 Integration Demo endpoint.

    Calls step4_rule_engine to generate report,
    then calls step5_llm_feedback to add LLM suggestions,
    writes to artifacts/step5_demo_report.json, and returns report.
    """
    # Fixed demo data: 3 triggers covering weight flip & tie-break scenarios
    demo_triggered_triggers = [
        {
            "id": "demo_base",
            "impact_score": 0.6,
            "severity": "P1",
            "conflict_priority": 2,
            "trigger_count": 3,
            "evidence": {
                "time_ranges": [{"start_ms": 1000, "end_ms": 5000}],
                "text_snippets": ["demo base rule snippet"],
            },
        },
        {
            "id": "demo_boosted",
            "impact_score": 0.5,
            "severity": "P2",
            "conflict_priority": 3,
            "trigger_count": 2,
            "evidence": {
                "time_ranges": [{"start_ms": 6000, "end_ms": 10000}],
                "text_snippets": ["demo boosted rule snippet 1", "demo boosted rule snippet 2"],
            },
        },
        {
            "id": "demo_tie_a",
            "impact_score": 0.4,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 5,
            "evidence": {
                "time_ranges": [{"start_ms": 11000, "end_ms": 15000}],
                "text_snippets": ["demo tie-break A"],
            },
        },
        {
            "id": "demo_tie_b",
            "impact_score": 0.4,
            "severity": "P0",
            "conflict_priority": 1,
            "trigger_count": 3,
            "evidence": {
                "time_ranges": [{"start_ms": 16000, "end_ms": 20000}],
                "text_snippets": ["demo tie-break B"],
            },
        },
    ]

    # Weight override to demonstrate flip
    demo_pack_weights = {"demo_boosted": 2.5}

    # Call Step4 integration layer
    report = step4_rule_engine(demo_triggered_triggers, demo_pack_weights)

    # Call Step5 LLM feedback
    report = step5_llm_feedback(report)

    # Ensure artifacts directory exists
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write to artifacts/step5_demo_report.json
    output_path = artifacts_dir / "step5_demo_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"step5 demo report generated path={output_path}")

    return report


if __name__ == "__main__":
    import uvicorn

    print("startup ok")

    # Pre-generate mock report on startup
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    output_path = artifacts_dir / "mock_report.json"
    report = build_mock_report()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"mock report generated path={output_path}")

    uvicorn.run(app, host="127.0.0.1", port=8000)
