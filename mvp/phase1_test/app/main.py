"""FastAPI application with /health, /mock/report, and /pipeline/step4_demo endpoints."""

import json
import os
import uuid
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.mock_report import build_mock_report
from app.pipeline.step4_rule_engine import step4_rule_engine
from app.pipeline.step5_llm_feedback import step5_llm_feedback
from app.pipeline.full_pipeline import run_step1_to_step5, run_step1_to_step6
from app.audio.ffmpeg_transcode import transcode_to_16k_mono_wav

app = FastAPI()

# ==================== Phase 1: Audio Upload ====================

ALLOWED_CONTENT_TYPES = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
}

UPLOADS_DIR = Path(__file__).parent.parent / "artifacts" / "uploads"


def _ensure_uploads_dir():
    """Ensure uploads directory exists."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _infer_extension(filename: Optional[str], content_type: str) -> str:
    """Infer file extension from filename or content_type."""
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else None
        if ext and ext in ["webm", "wav", "ogg", "mp3"]:
            return ext
    # Try from content_type
    if content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[content_type]
    return "bin"


@app.post("/api/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload audio file endpoint.
    
    Accepts: audio/webm, audio/wav, audio/ogg, audio/mpeg
    Returns: upload_id, saved_path, content_type, size_bytes
    """
    _ensure_uploads_dir()
    
    # Validate file presence
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="file missing")
    
    # Validate content type
    content_type = file.content_type or ""
    # Handle "audio/webm;codecs=opus" format
    base_content_type = content_type.split(";")[0].strip()
    
    if base_content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content-type: {content_type}. Allowed: {list(ALLOWED_CONTENT_TYPES.keys())}"
        )
    
    # Generate upload_id
    upload_id = str(uuid.uuid4())
    
    # Infer extension
    ext = _infer_extension(file.filename, base_content_type)
    
    # Build saved path
    saved_filename = f"{upload_id}.{ext}"
    saved_path = UPLOADS_DIR / saved_filename
    meta_path = UPLOADS_DIR / f"{upload_id}.meta.json"
    
    # Stream write file
    total_size = 0
    with open(saved_path, "wb") as f:
        while True:
            chunk = await file.read(8192)
            if not chunk:
                break
            f.write(chunk)
            total_size += len(chunk)
    
    # Write meta json
    meta = {
        "upload_id": upload_id,
        "original_filename": file.filename,
        "content_type": content_type,
        "saved_path": f"artifacts/uploads/{saved_filename}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "size_bytes": total_size,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return {
        "ok": True,
        "upload_id": upload_id,
        "saved_path": f"artifacts/uploads/{saved_filename}",
        "content_type": content_type,
        "size_bytes": total_size,
    }


@app.get("/api/uploads/latest")
def get_latest_uploads(limit: int = Query(10, le=100)):
    """
    Get latest uploaded audio files metadata.
    
    Returns up to `limit` most recent uploads based on meta.json files.
    """
    _ensure_uploads_dir()
    
    metas = []
    for meta_file in UPLOADS_DIR.glob("*.meta.json"):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                metas.append(meta)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by created_at descending
    metas.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"ok": True, "uploads": metas[:limit]}


# ==================== Phase 2: Analyze from Upload ====================

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"


def _ensure_artifacts_dir():
    """Ensure artifacts directory exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _find_uploaded_file(upload_id: str) -> Optional[Path]:
    """
    Find uploaded file by upload_id.
    
    Searches for files matching:
    - <upload_id>.webm
    - <upload_id>.wav
    - <upload_id>.ogg
    - <upload_id>.mp3
    - <upload_id>.bin
    
    Returns the path if found, None otherwise.
    """
    supported_exts = ["webm", "wav", "ogg", "mp3", "bin"]
    
    for ext in supported_exts:
        candidate = UPLOADS_DIR / f"{upload_id}.{ext}"
        if candidate.exists():
            return candidate
    
    return None


@app.post("/pipeline/run_from_upload")
def run_from_upload(request: dict):
    """
    Phase 2: Run full pipeline (Step1-6) from uploaded audio.
    
    Request JSON:
    {
        "upload_id": "<uuid>",
        "use_llm": 0|1  # default 0
    }
    
    Returns: ReportResponse JSON with scores, report_view, warnings, etc.
    
    Errors:
    - 400: missing upload_id
    - 404: upload not found
    - 500: ffmpeg error or unexpected error
    """
    _ensure_artifacts_dir()
    _ensure_uploads_dir()
    
    # Validate request
    upload_id = request.get("upload_id")
    if not upload_id:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "upload_id required",
                "hint": "Request body must include upload_id"
            }
        )
    
    use_llm = bool(request.get("use_llm", 0))
    
    # Find uploaded file
    input_file = _find_uploaded_file(upload_id)
    if not input_file:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "error": f"upload not found: {upload_id}",
                "hint": "Check that the file was uploaded via /api/upload_audio"
            }
        )
    
    # Check ffmpeg availability
    if not shutil.which("ffmpeg"):
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "ffmpeg not found",
                "hint": "Install ffmpeg and add to PATH, or download from https://ffmpeg.org/download.html"
            }
        )
    
    # Transcode to 16k mono wav
    output_wav = UPLOADS_DIR / f"{upload_id}_16k.wav"
    
    try:
        transcode_to_16k_mono_wav(input_file, output_wav)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "ffmpeg failed",
                "hint": str(e)
            }
        )
    
    # Verify transcoded file
    if not output_wav.exists() or output_wav.stat().st_size == 0:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "transcoding produced empty output",
                "hint": "The uploaded audio file may be corrupted"
            }
        )
    
    # Run Step1-6 pipeline
    try:
        report = run_step1_to_step6(
            audio_path=str(output_wav),
            use_llm=use_llm
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "pipeline failed",
                "hint": str(e)
            }
        )
    
    # Save debug artifact
    _ensure_artifacts_dir()
    debug_output = ARTIFACTS_DIR / f"step1_6_from_upload_{upload_id}.json"
    with open(debug_output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"step1_6 from upload report generated path={debug_output}")
    
    return report


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


@app.get("/pipeline/step1_5_demo")
def pipeline_step1_5_demo(
    audio: Optional[str] = Query(None, description="Path to local audio file"),
    use_llm: int = Query(1, description="Use LLM (1) or force fallback (0)"),
    save: int = Query(1, description="Save report to artifacts (1) or not (0)")
) -> dict:
    """
    Step1-5 Full Pipeline Demo endpoint.

    Runs complete pipeline: Step1 ASR -> Step2 Pace/Pause -> Step3 Text Features
    -> Step4 Rule Engine (Top5) -> Step5 LLM Feedback.

    Args:
        audio: Optional path to audio file. If not provided, uses SAMPLE_AUDIO_PATH env var.
        use_llm: 1 to use LLM, 0 to force template fallback (default: 1)
        save: 1 to save report to artifacts, 0 to skip (default: 1)

    Returns:
        Complete ReportResponse dict.

    Error:
        400 JSON error if audio path not provided and SAMPLE_AUDIO_PATH not set.
    """
    # Resolve audio path
    audio_path = audio
    if audio_path is None:
        audio_path = os.environ.get("SAMPLE_AUDIO_PATH")

    if audio_path is None:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "audio path required",
                "hint": "set SAMPLE_AUDIO_PATH env var or pass ?audio=..."
            }
        )

    # Check file exists
    if not Path(audio_path).exists():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": f"audio file not found: {audio_path}",
                "hint": "Ensure the file exists and path is correct"
            }
        )

    # Run full pipeline
    report = run_step1_to_step5(
        audio_path=audio_path,
        use_llm=bool(use_llm)
    )

    # Save if requested
    if save:
        artifacts_dir = Path(__file__).parent.parent / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        output_path = artifacts_dir / "step1_5_demo_report.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"step1_5 demo report generated path={output_path}")

    return report


@app.get("/pipeline/step1_6_demo")
def pipeline_step1_6_demo(
    audio: Optional[str] = Query(None, description="Path to local audio file"),
    use_llm: int = Query(0, description="Use LLM (1) or force fallback (0), default 0"),
    save: int = Query(1, description="Save report to artifacts (1) or not (0), default 1")
) -> dict:
    """
    Step1-6 Full Pipeline Demo endpoint.

    Runs complete pipeline: Step1 ASR -> Step2 Pace/Pause -> Step3 Text Features
    -> Step4 Rule Engine (Top5) -> Step5 LLM Feedback -> Step6 Report Aggregation.

    Returns final ReportResponse with:
    - scores.overall (0-100, deterministic)
    - report_view (chart_data + highlights)
    - warnings (merged from Step4/Step5)

    Args:
        audio: Optional path to audio file. If not provided, uses SAMPLE_AUDIO_PATH env var.
        use_llm: 1 to use LLM, 0 to force template fallback (default: 0)
        save: 1 to save report to artifacts, 0 to skip (default: 1)

    Returns:
        Complete ReportResponse dict with report_view.

    Error:
        400 JSON error if audio path not provided and SAMPLE_AUDIO_PATH not set.
    """
    # Resolve audio path
    audio_path = audio
    if audio_path is None:
        audio_path = os.environ.get("SAMPLE_AUDIO_PATH")

    if audio_path is None:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "audio path required",
                "hint": "set SAMPLE_AUDIO_PATH env var or pass ?audio=..."
            }
        )

    # Check file exists
    if not Path(audio_path).exists():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": f"audio file not found: {audio_path}",
                "hint": "Ensure the file exists and path is correct"
            }
        )

    # Run full pipeline
    report = run_step1_to_step6(
        audio_path=audio_path,
        use_llm=bool(use_llm)
    )

    # Save if requested
    if save:
        artifacts_dir = Path(__file__).parent.parent / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        output_path = artifacts_dir / "step1_6_demo_report.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"step1_6 demo report generated path={output_path}")

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
