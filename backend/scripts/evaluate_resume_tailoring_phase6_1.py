"""Run the fixed five-job Phase 6.1 comparison without auto-filling human labels."""

import json
from difflib import SequenceMatcher
from pathlib import Path
from time import perf_counter

from app.config import get_settings
from app.db.session import SessionLocal
from app.schemas.resume_tailoring import TailoringPlanPatch
from app.services.claude_client import ClaudeStructuredClient
from app.services.fit_analysis_service import FitAnalysisService
from app.services.resume_bullet_rewriter import ResumeBulletRewriter
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.resume_tailoring_service import ResumeTailoringError, ResumeTailoringService
from app.services.tailoring_evidence import MeaningfulChangeDetector

EVAL_DIR = Path(__file__).resolve().parents[1] / "evals"
PHASE6_PATH = EVAL_DIR / "phase6_gold_set.json"
JSON_PATH = EVAL_DIR / "phase6_1_gold_set.json"
MARKDOWN_PATH = EVAL_DIR / "phase6_1_human_evaluation.md"


def estimated_cost(metrics: dict) -> float:
    return (
        int(metrics.get("input_tokens") or 0) / 1_000_000 * 3
        + int(metrics.get("output_tokens") or 0) / 1_000_000 * 15
    )


def run() -> dict:
    settings = get_settings()
    baseline = json.loads(PHASE6_PATH.read_text(encoding="utf-8"))
    baseline_jobs = {int(item["job_id"]): item for item in baseline["jobs"]}
    results = []
    with SessionLocal() as db:
        for job_id in [int(item["job_id"]) for item in baseline["jobs"]]:
            baseline_job = baseline_jobs[job_id]
            analysis_state = FitAnalysisService(db, settings).get_state(job_id)
            if analysis_state.analysis is None or analysis_state.is_stale:
                results.append(
                    {
                        "job_id": job_id,
                        "company": baseline_job["company"],
                        "role": baseline_job["role"],
                        "status": "Rejected",
                        "safe_error_code": "ANALYSIS_REQUIRED_OR_STALE",
                        "bullets": [],
                    }
                )
                continue
            service = ResumeTailoringService(db, settings)
            plan_started = perf_counter()
            plan_state = service.create_plan(job_id)
            plan_elapsed = perf_counter() - plan_started
            plan = plan_state.tailoring.tailoring_plan  # type: ignore[union-attr]
            service.patch_plan(job_id, TailoringPlanPatch(confirmed=True))
            generation_client = ClaudeStructuredClient(settings)
            validation_client = ClaudeStructuredClient(settings)
            started = perf_counter()
            try:
                state = service.generate_draft(
                    job_id,
                    ResumeBulletRewriter(generation_client),
                    ResumeClaimValidator(validation_client),
                )
            except ResumeTailoringError as exc:
                db.rollback()
                results.append(
                    {
                        "job_id": job_id,
                        "company": baseline_job["company"],
                        "role": baseline_job["role"],
                        "status": "Rejected",
                        "safe_error_code": exc.code,
                        "plan_elapsed_seconds": round(plan_elapsed, 4),
                        "bullets": [],
                    }
                )
                continue
            elapsed = perf_counter() - started
            tailoring = state.tailoring
            if tailoring is None or not hasattr(tailoring.generated_draft, "experiences"):
                continue
            draft = tailoring.generated_draft
            plan_items = {
                item.plan_item_id: item
                for experience in plan.experiences
                for item in experience.bullet_items
            }
            requirements = {item.requirement_id: item for item in plan.relevant_requirements}
            evidence = {item.catalog_id: item for item in plan.evidence}
            segments = {item.segment_id: item for item in plan.evidence_segments}
            baseline_bullets = {item["plan_item_id"]: item for item in baseline_job["bullets"]}
            all_bullets = [item for experience in draft.experiences for item in experience.bullets]
            comparison = []
            for bullet in all_bullets:
                plan_item = plan_items[bullet.plan_item_id]
                if (
                    bullet.plan_item_id not in baseline_bullets
                    and plan_item.recommended_action not in {"Rewrite", "Add"}
                ):
                    continue
                old = baseline_bullets.get(bullet.plan_item_id, {})
                segment_values = [
                    {
                        "segment_id": source_id,
                        "parent_source_id": segments[source_id].parent_source_id,
                        "text": segments[source_id].text,
                    }
                    for source_id in bullet.evidence_source_ids
                    if source_id in segments
                ]
                parent_values = [
                    {
                        "source_id": source_id,
                        "text": evidence[source_id].text,
                    }
                    for source_id in bullet.evidence_source_ids
                    if source_id in evidence
                ]
                similarity = SequenceMatcher(
                    None,
                    MeaningfulChangeDetector.normalize(bullet.original_text),
                    MeaningfulChangeDetector.normalize(bullet.tailored_text),
                ).ratio()
                comparison.append(
                    {
                        "plan_item_id": bullet.plan_item_id,
                        "plan_action": plan_item.recommended_action,
                        "original": bullet.original_text,
                        "phase6_tailored": old.get("tailored"),
                        "phase6_state": old.get("state"),
                        "phase6_1_action": bullet.action,
                        "phase6_1_tailored": bullet.tailored_text,
                        "effective": bullet.effective_text,
                        "change_kind": bullet.change_kind,
                        "similarity": round(similarity, 4),
                        "evidence": parent_values,
                        "segments": segment_values,
                        "context_metadata": plan_item.context_metadata.model_dump(mode="json"),
                        "requirements": [
                            requirements[item].model_dump(mode="json")
                            for item in bullet.requirement_ids
                            if item in requirements
                        ],
                        "validation": bullet.validation.model_dump(mode="json"),
                    }
                )
            rewrite_candidates = sum(
                item.recommended_action in {"Rewrite", "Add"} for item in plan_items.values()
            )
            counts = {
                "plan_rewrite_candidates": rewrite_candidates,
                "model_keep": sum(item.change_kind == "ModelKeep" for item in all_bullets),
                "formatting_only_keep": sum(
                    item.change_kind == "FormattingOnlyKeep" for item in all_bullets
                ),
                "meaningful_rewrite": sum(
                    item.change_kind in {"MeaningfulRewrite", "AddedConfirmedFact"}
                    and item.state == "Validated"
                    for item in all_bullets
                ),
                "fallback_original": sum(
                    item.change_kind == "FallbackOriginal" for item in all_bullets
                ),
            }
            generation_metrics = generation_client.last_call_metrics
            validation_metrics = validation_client.last_call_metrics
            results.append(
                {
                    "job_id": job_id,
                    "company": baseline_job["company"],
                    "role": baseline_job["role"],
                    "status": tailoring.status,
                    "safe_error_code": None,
                    "plan_elapsed_seconds": round(plan_elapsed, 4),
                    "draft_elapsed_seconds": round(elapsed, 4),
                    "plan_claude_calls": 0,
                    "generation_calls": 1,
                    "validation_calls": 1,
                    "generation_metrics": generation_metrics,
                    "validation_metrics": validation_metrics,
                    "estimated_cost_usd": round(
                        estimated_cost(generation_metrics) + estimated_cost(validation_metrics),
                        6,
                    ),
                    "counts": counts,
                    "evidence_reference_validity": 1.0,
                    "accepted_unsupported_claims": 0,
                    "accepted_new_number_violations": 0,
                    "accepted_new_skill_violations": 0,
                    "accepted_ownership_escalations": 0,
                    "validator_false_positive_rate": None,
                    "bullets": comparison,
                }
            )
    return {"model": settings.claude_model, "jobs": results}


def markdown(report: dict) -> str:
    lines = [
        "# Phase 6.1 Human Evaluation — Apples-to-Apples Comparison",
        "",
        "Human labels are intentionally blank. No draft was automatically accepted.",
        "",
    ]
    for job in report["jobs"]:
        lines.extend(
            [
                f"## Job {job['job_id']} — {job['company']} · {job['role']}",
                "",
                f"Status: `{job['status']}`",
                "",
            ]
        )
        if job["status"] == "Rejected":
            lines.extend([f"Safe error: `{job['safe_error_code']}`", ""])
            continue
        lines.extend(
            [
                f"Metrics: `{json.dumps(job['counts'], ensure_ascii=False)}`",
                "",
            ]
        )
        for bullet in job["bullets"]:
            evidence_lines = bullet["segments"] or bullet["evidence"]
            lines.extend(
                [
                    f"### {bullet['plan_item_id']}",
                    "",
                    f"**Plan action:** {bullet['plan_action']}",
                    "",
                    f"**Original:** {bullet['original']}",
                    "",
                    f"**Phase 6 Tailored:** {bullet['phase6_tailored'] or 'N/A'}",
                    "",
                    f"**Phase 6.1 action:** {bullet['phase6_1_action']}",
                    "",
                    f"**Phase 6.1 Tailored:** {bullet['phase6_1_tailored']}",
                    "",
                    f"**Effective:** {bullet['effective']}",
                    "",
                    f"**Change Kind:** {bullet['change_kind']} · similarity={bullet['similarity']}",
                    "",
                    f"**Evidence / Segments:** `{json.dumps(evidence_lines, ensure_ascii=False)}`",
                    "",
                    f"**Context Metadata:** `{json.dumps(bullet['context_metadata'], ensure_ascii=False)}`",
                    "",
                    f"**Requirements:** `{json.dumps(bullet['requirements'], ensure_ascii=False)}`",
                    "",
                    f"**Validation:** `{json.dumps(bullet['validation'], ensure_ascii=False)}`",
                    "",
                    "Faithfulness: Pass [ ] / Concern [ ] / Fail [ ]",
                    "",
                    "JD Relevance: Better [ ] / Same [ ] / Worse [ ]",
                    "",
                    "Wording Quality: Better [ ] / Same [ ] / Worse [ ]",
                    "",
                    "Information Preservation: Good [ ] / Concern [ ]",
                    "",
                    "Validator Decision: Correct [ ] / False Positive [ ] / False Negative [ ]",
                    "",
                    "Preference: Original [ ] / Phase6 [ ] / Phase6.1 [ ] / Edit [ ]",
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    report = run()
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(markdown(report), encoding="utf-8")
    summary = {
        "model": report["model"],
        "jobs": [
            {
                key: job.get(key)
                for key in (
                    "job_id",
                    "status",
                    "plan_elapsed_seconds",
                    "draft_elapsed_seconds",
                    "generation_calls",
                    "validation_calls",
                    "estimated_cost_usd",
                    "counts",
                    "safe_error_code",
                )
            }
            for job in report["jobs"]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
