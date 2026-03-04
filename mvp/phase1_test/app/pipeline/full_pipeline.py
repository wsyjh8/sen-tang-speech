"""
Full Pipeline Orchestrator (Step1 -> Step6).

Orchestrates the complete pipeline:
Step1 ASR -> Step2 Pace/Pause -> Step3 Text Features -> Step4 Rule Engine -> Step5 LLM Feedback -> Step6 Report Aggregation
"""

from typing import Dict, Any, Optional

from app.asr.step1_asr import run_step1_asr
from app.acoustic.step2_pace_pause import run_step2_pace_pause
from app.text_features.step3_text_features import run_step3_text_features
from app.pipeline.step4_rule_engine import step4_from_artifacts
from app.pipeline.step5_llm_feedback import step5_llm_feedback
from app.pipeline.step6_report_aggregation import aggregate_report


def run_step1_to_step5(
    audio_path: str,
    use_llm: bool = True,
    pack_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Run complete pipeline from Step1 to Step5.

    Args:
        audio_path: Path to local audio file (WAV 16kHz mono 16-bit)
        use_llm: If False, skip LLM call and use template fallback
        pack_weights: Optional dict mapping trigger.id -> weight override

    Returns:
        Complete ReportResponse dict with all fields populated.
    """
    # Step1: ASR
    step1_result = run_step1_asr(audio_path=audio_path, language="zh", model_size="small")

    # Step2: Pace/Pause
    step2_result = run_step2_pace_pause(
        audio_path=audio_path,
        asr_result=step1_result
    )

    # Step3: Text Features
    step3_result = run_step3_text_features(
        step1_result=step1_result,
        step2_result=step2_result
    )

    # Step4: Rule Engine (from artifacts)
    report = step4_from_artifacts(
        step1_result=step1_result,
        step2_result=step2_result,
        step3_result=step3_result,
        pack_weights=pack_weights
    )

    # Enrich report with metrics for Step5 LLM feedback
    report["_step2_wpm"] = step2_result.get("wpm")
    report["_step2_long_pause_count"] = step2_result.get("long_pause_count")
    report["_step2_max_pause_ms"] = step2_result.get("max_pause_ms")

    text_features = step3_result.get("text_features", {})
    report["_step3_filler_ratio"] = text_features.get("filler_ratio")
    report["_step3_repeat_ratio"] = text_features.get("repeat_ratio")

    # Step5: LLM Feedback
    report = step5_llm_feedback(report, use_llm=use_llm)

    # Clean up internal fields before returning
    internal_keys = [
        "_step2_wpm", "_step2_long_pause_count", "_step2_max_pause_ms",
        "_step3_filler_ratio", "_step3_repeat_ratio",
    ]
    for key in internal_keys:
        report.pop(key, None)

    return report


def run_step1_to_step6(
    audio_path: str,
    use_llm: bool = True,
    pack_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Run complete pipeline from Step1 to Step6.

    Args:
        audio_path: Path to local audio file (WAV 16kHz mono 16-bit)
        use_llm: If False, skip LLM call and use template fallback
        pack_weights: Optional dict mapping trigger.id -> weight override

    Returns:
        Complete ReportResponse dict with all fields populated including:
        - scores.overall (0-100, deterministic)
        - report_view (chart_data + highlights)
        - warnings (merged from Step4/Step5)
    """
    # Step1: ASR
    step1_result = run_step1_asr(audio_path=audio_path, language="zh", model_size="small")

    # Step2: Pace/Pause
    step2_result = run_step2_pace_pause(
        audio_path=audio_path,
        asr_result=step1_result
    )

    # Step3: Text Features
    step3_result = run_step3_text_features(
        step1_result=step1_result,
        step2_result=step2_result
    )

    # Step4: Rule Engine (from artifacts)
    step4_report = step4_from_artifacts(
        step1_result=step1_result,
        step2_result=step2_result,
        step3_result=step3_result,
        pack_weights=pack_weights
    )

    # Enrich report with metrics for Step5 LLM feedback
    step4_report["_step2_wpm"] = step2_result.get("wpm")
    step4_report["_step2_long_pause_count"] = step2_result.get("long_pause_count")
    step4_report["_step2_max_pause_ms"] = step2_result.get("max_pause_ms")

    text_features = step3_result.get("text_features", {})
    step4_report["_step3_filler_ratio"] = text_features.get("filler_ratio")
    step4_report["_step3_repeat_ratio"] = text_features.get("repeat_ratio")

    # Step5: LLM Feedback
    step5_report = step5_llm_feedback(step4_report, use_llm=use_llm)

    # Step6: Report Aggregation
    final_report = aggregate_report(
        step1_asr=step1_result,
        step2_pace_pause=step2_result,
        step4_rule_engine=step5_report,
        step5_llm_feedback=step5_report,
    )

    return final_report
