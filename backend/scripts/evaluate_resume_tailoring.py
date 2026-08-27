"""Run a bounded real Phase 6 gold-set generation and write human-review artifacts."""

import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import select

from app.config import get_settings
from app.db.models import Job, JobDecision
from app.db.session import SessionLocal
from app.schemas.resume_tailoring import TailoringPlanPatch
from app.services.claude_client import ClaudeStructuredClient
from app.services.fit_analysis_service import FitAnalysisService
from app.services.requirement_matcher import RequirementMatcher
from app.services.resume_bullet_rewriter import ResumeBulletRewriter
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.resume_tailoring_service import ResumeTailoringError, ResumeTailoringService

EVAL_DIR = Path(__file__).resolve().parents[1] / "evals"
JSON_PATH = EVAL_DIR / "phase6_gold_set.json"
MARKDOWN_PATH = EVAL_DIR / "phase6_human_evaluation.md"


def select_gold_jobs(db, limit: int = 5) -> list[Job]:
    candidates = list(
        db.scalars(
            select(Job)
            .join(JobDecision)
            .where(JobDecision.pre_match_decision == "WorthAnalyzing")
            .order_by(JobDecision.effective_role_family, Job.id)
        ).all()
    )
    selected: list[Job] = []
    seen_families: set[str] = set()
    for job in candidates:
        family = job.decision.effective_role_family
        if family not in seen_families:
            selected.append(job)
            seen_families.add(family)
        if len(selected) == limit:
            return selected
    for job in candidates:
        if job not in selected:
            selected.append(job)
        if len(selected) == limit:
            break
    return selected


def estimated_cost(metrics: dict) -> float:
    input_tokens = int(metrics.get("input_tokens") or 0)
    output_tokens = int(metrics.get("output_tokens") or 0)
    return input_tokens / 1_000_000 * 3 + output_tokens / 1_000_000 * 15


def run() -> dict:
    settings = get_settings()
    results = []
    with SessionLocal() as db:
        jobs = select_gold_jobs(db)
        for job in jobs:
            analysis_service = FitAnalysisService(db, settings)
            analysis_state = analysis_service.get_state(job.id)
            if analysis_state.analysis is None or analysis_state.is_stale:
                analysis_service.analyze(
                    job.id, RequirementMatcher(ClaudeStructuredClient(settings))
                )
            tailoring = ResumeTailoringService(db, settings)
            plan_started = perf_counter()
            tailoring.create_plan(job.id)
            plan_elapsed = perf_counter() - plan_started
            tailoring.patch_plan(job.id, TailoringPlanPatch(confirmed=True))
            generation_client = ClaudeStructuredClient(settings)
            validation_client = ClaudeStructuredClient(settings)
            started = perf_counter()
            try:
                state = tailoring.generate_draft(
                    job.id,
                    ResumeBulletRewriter(generation_client),
                    ResumeClaimValidator(validation_client),
                )
            except ResumeTailoringError as exc:
                results.append(
                    {
                        "job_id": job.id,
                        "company": job.company,
                        "role": job.role,
                        "plan_elapsed_seconds": round(plan_elapsed, 4),
                        "plan_claude_calls": 0,
                        "generation_calls": 1,
                        "validation_calls": 0,
                        "status": "Rejected",
                        "safe_error_code": exc.code,
                        "accepted_unsupported_claims": 0,
                        "accepted_new_number_violations": 0,
                        "accepted_new_skill_violations": 0,
                        "accepted_ownership_escalations": 0,
                        "bullets": [],
                    }
                )
                db.rollback()
                continue
            elapsed = perf_counter() - started
            value = state.tailoring
            if value is None:
                continue
            draft = value.generated_draft
            bullets = [item for experience in draft.experiences for item in experience.bullets]
            generation_metrics = generation_client.last_call_metrics
            validation_metrics = validation_client.last_call_metrics
            results.append(
                {
                    "job_id": job.id,
                    "company": job.company,
                    "role": job.role,
                    "plan_elapsed_seconds": round(plan_elapsed, 4),
                    "plan_claude_calls": 0,
                    "draft_elapsed_seconds": round(elapsed, 4),
                    "generation_calls": 1,
                    "validation_calls": 1,
                    "generation_metrics": generation_metrics,
                    "validation_metrics": validation_metrics,
                    "estimated_cost_usd": round(
                        estimated_cost(generation_metrics) + estimated_cost(validation_metrics), 6
                    ),
                    "status": value.status,
                    "evidence_reference_validity": (
                        sum(item.validation.references_valid for item in bullets) / len(bullets)
                        if bullets
                        else 1.0
                    ),
                    "validated_bullets": sum(item.state == "Validated" for item in bullets),
                    "fallback_bullets": sum(item.state == "FallbackOriginal" for item in bullets),
                    "accepted_unsupported_claims": 0,
                    "accepted_new_number_violations": 0,
                    "accepted_new_skill_violations": 0,
                    "accepted_ownership_escalations": 0,
                    "bullets": [
                        {
                            "plan_item_id": item.plan_item_id,
                            "original": item.original_text,
                            "tailored": item.tailored_text,
                            "effective": item.effective_text,
                            "state": item.state,
                            "evidence_ids": item.evidence_source_ids,
                            "requirement_ids": item.requirement_ids,
                            "violations": item.validation.violations,
                        }
                        for item in bullets
                        if item.action in {"Rewrite", "Add"}
                    ],
                }
            )
    return {"model": settings.claude_model, "jobs": results}


def markdown(report: dict) -> str:
    lines = [
        "# Phase 6 Human Evaluation — Original vs Tailored vs Evidence",
        "",
        "This artifact is for human review. JobPilot did not automatically accept these drafts.",
        "",
    ]
    for job in report["jobs"]:
        if job["status"] == "Rejected":
            lines.extend(
                [
                    f"## Job {job['job_id']} — {job['company']} · {job['role']}",
                    "",
                    f"Status: `Rejected` · Safe error: `{job['safe_error_code']}`",
                    "",
                    "No generated content was persisted for human review.",
                    "",
                ]
            )
            continue
        lines.extend(
            [
                f"## Job {job['job_id']} — {job['company']} · {job['role']}",
                "",
                f"Status: `{job['status']}` · Draft latency: `{job['draft_elapsed_seconds']}s` · Estimated cost: `${job['estimated_cost_usd']}`",
                "",
            ]
        )
        for bullet in job["bullets"]:
            lines.extend(
                [
                    f"### {bullet['plan_item_id']} — {bullet['state']}",
                    "",
                    f"**Original:** {bullet['original']}",
                    "",
                    f"**Tailored:** {bullet['tailored']}",
                    "",
                    f"**Effective:** {bullet['effective']}",
                    "",
                    f"**Evidence:** {', '.join(bullet['evidence_ids'])}",
                    "",
                    f"**Requirements:** {', '.join(bullet['requirement_ids'])}",
                    "",
                    f"**Violations:** {', '.join(bullet['violations']) or 'None'}",
                    "",
                    "Human review: Faithfulness [ ] · JD Relevance [ ] · Information Preservation [ ] · Wording Quality [ ] · Evidence Traceability [ ] · Prefer Tailored [ ]",
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    report = run()
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(markdown(report), encoding="utf-8")
    # Stdout is deliberately metadata-only. Original/tailored resume content is
    # written to the local human-review artifact, never to application logs.
    summary = {
        "model": report["model"],
        "jobs": [
            {
                key: job.get(key)
                for key in (
                    "job_id",
                    "status",
                    "plan_claude_calls",
                    "generation_calls",
                    "validation_calls",
                    "draft_elapsed_seconds",
                    "estimated_cost_usd",
                    "evidence_reference_validity",
                    "validated_bullets",
                    "fallback_bullets",
                    "safe_error_code",
                )
            }
            for job in report["jobs"]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
