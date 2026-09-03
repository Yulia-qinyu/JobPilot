import logging
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Job, JobAnalysis, JobDecision, UserProfile
from app.repositories.job_decision_repository import JobDecisionRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import JDRequirements
from app.schemas.job_decision import (
    DecisionJobItem,
    DecisionJobPage,
    DecisionRecomputeResult,
    DecisionSummary,
    EligibilityStatus,
    FinalDecision,
    JobDecisionOverride,
    JobDecisionRead,
    PreMatchDecision,
)
from app.services.analysis_freshness import analysis_identity_is_current
from app.services.eligibility_service import EligibilityService
from app.services.evidence_catalog import EvidenceCatalogBuilder, canonical_hash
from app.services.matcher_client import active_matcher_model
from app.services.requirement_catalog import RequirementCatalogBuilder
from app.services.role_classifier import RoleClassifier
from app.services.target_role_fit_service import TargetRoleFitService


class JobDecisionError(ValueError):
    pass


class JobDecisionNotFoundError(JobDecisionError):
    pass


class JobDecisionService:
    ENGINE_VERSION = "job-decision-v1"
    MAX_RECOMPUTE = 2_000

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobDecisionRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.role_classifier = RoleClassifier()
        self.eligibility = EligibilityService()
        self.role_fit = TargetRoleFitService()
        self.evidence_builder = EvidenceCatalogBuilder()
        self.requirement_builder = RequirementCatalogBuilder()
        self.settings = get_settings()

    def get(self, job_id: int) -> JobDecisionRead:
        decision = self.repo.get(job_id)
        if decision is None:
            raise JobDecisionNotFoundError("Job decision not found.")
        return JobDecisionRead.model_validate(decision)

    def recompute(self, job_ids: list[int] | None = None) -> DecisionRecomputeResult:
        started = perf_counter()
        if job_ids is not None:
            job_ids = list(dict.fromkeys(job_ids))
            if len(job_ids) > self.MAX_RECOMPUTE:
                raise JobDecisionError("At most 2000 jobs can be recomputed at once.")
        jobs = self.repo.jobs_for_recompute(job_ids)
        if job_ids is None and len(jobs) > self.MAX_RECOMPUTE:
            raise JobDecisionError("At most 2000 jobs can be recomputed at once.")
        profile = self.profile_repo.get_full_profile()
        candidate_hash = self._candidate_hash(profile)
        target_hash = self._target_roles_hash(profile)
        evidence_hashes = self._evidence_hashes(profile)
        failures = 0
        for job in jobs:
            try:
                self._evaluate_job(job, profile, candidate_hash, target_hash, evidence_hashes)
            except (TypeError, ValueError):
                failures += 1
                if job.decision is not None:
                    job.decision.is_stale = True
        self.repo.commit()
        result = DecisionRecomputeResult(
            requested=len(job_ids) if job_ids is not None else len(jobs),
            processed=len(jobs) - failures,
            failed=failures,
            elapsed_seconds=round(perf_counter() - started, 4),
        )
        logging.getLogger(__name__).info(
            "job_decision_recompute_completed requested=%s processed=%s failed=%s "
            "elapsed_seconds=%.4f claude_calls=0",
            result.requested,
            result.processed,
            result.failed,
            result.elapsed_seconds,
        )
        return result

    def page(self, **filters: object) -> DecisionJobPage:
        page = int(filters["page"])
        page_size = int(filters["page_size"])
        rows, total = self.repo.page(**filters)  # type: ignore[arg-type]
        items = []
        for job, decision, analysis in rows:
            items.append(
                DecisionJobItem(
                    id=job.id,
                    company=job.company,
                    role=job.role,
                    location=job.location,
                    source=job.source,
                    status=job.status,
                    application_status_id=job.application_status_id,
                    application_status_label=(job.application_status.label if job.application_status else None),
                    match_score=job.match_score if analysis is not None else None,
                    match_is_stale=analysis is not None
                    and (decision is None or decision.analysis_hash is None),
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    decision=JobDecisionRead.model_validate(decision) if decision else None,
                )
            )
        return DecisionJobPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )

    def summary(self) -> DecisionSummary:
        return DecisionSummary(**self.repo.summary())

    def update_overrides(self, job_id: int, payload: JobDecisionOverride) -> JobDecisionRead:
        decision = self.repo.get(job_id)
        if decision is None:
            self.recompute([job_id])
            decision = self.repo.get(job_id)
        if decision is None:
            raise JobDecisionNotFoundError("Job decision not found.")
        fields = payload.model_fields_set
        if "role_family_override" in fields:
            decision.role_family_override = payload.role_family_override
        if "eligibility_override" in fields:
            decision.eligibility_override = payload.eligibility_override
            if payload.eligibility_override is None and "eligibility_override_reason" not in fields:
                decision.eligibility_override_reason = None
        if "eligibility_override_reason" in fields:
            decision.eligibility_override_reason = self._clean_optional(
                payload.eligibility_override_reason
            )
        self.repo.commit()
        self.recompute([job_id])
        return self.get(job_id)

    def _evaluate_job(
        self,
        job: Job,
        profile: UserProfile,
        candidate_hash: str,
        target_hash: str,
        evidence_hashes: tuple[str, str] | None,
    ) -> JobDecision:
        classification = self.role_classifier.classify(job)
        eligibility = self.eligibility.evaluate(profile, job)
        existing = job.decision
        role_override = existing.role_family_override if existing else None
        eligibility_override = existing.eligibility_override if existing else None
        override_reason = existing.eligibility_override_reason if existing else None
        effective_family = role_override or classification.role_family
        effective_eligibility: EligibilityStatus = eligibility_override or eligibility.status
        target_fit = self.role_fit.evaluate(effective_family, profile.target_roles)
        pre_match, pre_reasons = self._pre_match(
            effective_eligibility,
            target_fit,
            profile.preferred_location,
            job.location,
        )
        analysis_hash, valid_analysis = self._valid_analysis(job, evidence_hashes)
        final_decision, final_reasons = self._final_decision(
            effective_eligibility,
            target_fit,
            valid_analysis,
        )
        values = {
            "auto_role_family": classification.role_family,
            "role_family_override": role_override,
            "effective_role_family": effective_family,
            "role_classification_confidence": classification.confidence,
            "role_classification_reasons": classification.reasons,
            "classifier_version": self.role_classifier.VERSION,
            "auto_eligibility_status": eligibility.status,
            "eligibility_override": eligibility_override,
            "effective_eligibility_status": effective_eligibility,
            "eligibility_reasons": eligibility.reasons,
            "blocking_requirements": eligibility.blocking_requirements,
            "unknown_requirements": eligibility.unknown_requirements,
            "eligibility_override_reason": override_reason,
            "target_role_fit": target_fit,
            "pre_match_decision": pre_match,
            "final_decision": final_decision,
            "decision_reasons": [*pre_reasons, *final_reasons],
            "candidate_hash": candidate_hash,
            "target_roles_hash": target_hash,
            "job_input_hash": self._job_hash(job),
            "analysis_hash": analysis_hash,
            "engine_version": self.ENGINE_VERSION,
            "is_stale": False,
            "evaluated_at": datetime.now(UTC),
        }
        if existing is None:
            existing = self.repo.add(JobDecision(job_id=job.id, **values))
            job.decision = existing
        else:
            for field, value in values.items():
                setattr(existing, field, value)
        return existing

    @staticmethod
    def _pre_match(
        eligibility: str,
        role_fit: str,
        preferred_location: str | None,
        job_location: str | None,
    ) -> tuple[PreMatchDecision, list[str]]:
        if eligibility == "Ineligible":
            return "Exclude", ["存在明确投递门槛冲突。"]
        if role_fit == "NotTarget":
            return "Exclude", ["岗位不属于当前目标方向。"]
        if JobDecisionService._location_mismatch(preferred_location, job_location):
            return "LowPriority", ["岗位城市与当前目标城市不一致。"]
        if eligibility in {"Eligible", "PossiblyEligible"} and role_fit in {
            "Primary",
            "Secondary",
        }:
            return "WorthAnalyzing", ["岗位属于核心目标方向，值得进一步匹配分析。"]
        return "LowPriority", ["当前方向或资格信息不足以列为优先分析岗位。"]

    @staticmethod
    def _final_decision(
        eligibility: str,
        role_fit: str,
        analysis: JobAnalysis | None,
    ) -> tuple[FinalDecision | None, list[str]]:
        if analysis is None:
            return None, []
        missing_hard = [
            item
            for item in analysis.requirement_matches
            if item.get("is_hard_requirement") and item.get("match_status") == "Missing"
        ]
        severe_hard = any(
            item.get("hard_requirement_category") in {"eligibility", "qualification"}
            for item in missing_hard
        )
        if eligibility == "Ineligible" or role_fit == "NotTarget" or severe_hard:
            return "Skip", ["存在明确门槛、非目标方向或强制资格缺口。"]
        if analysis.recommendation == "Skip" or analysis.match_score < 55:
            return "Skip", ["Phase 3 匹配结果低于建议投递范围。"]
        if eligibility == "PossiblyEligible":
            return "Consider", ["仍有投递资格条件需要确认。"]
        if (
            eligibility == "Eligible"
            and role_fit == "Primary"
            and analysis.match_score >= 85
            and analysis.recommendation == "Strong Apply"
            and not missing_hard
        ):
            return "Priority", ["核心目标岗位且 Phase 3 显示高度匹配。"]
        if (
            eligibility == "Eligible"
            and role_fit in {"Primary", "Secondary"}
            and analysis.match_score >= 70
            and analysis.recommendation in {"Apply", "Strong Apply"}
            and not missing_hard
        ):
            return "Apply", ["目标方向明确，且 Phase 3 达到建议投递区间。"]
        return "Consider", ["岗位存在一定匹配价值，但方向、门槛或深度仍需权衡。"]

    def _valid_analysis(
        self, job: Job, evidence_hashes: tuple[str, str] | None
    ) -> tuple[str | None, JobAnalysis | None]:
        analysis = job.analysis
        if analysis is None or evidence_hashes is None:
            return None, None
        jd_hash = self.requirement_builder.build(job.structured_jd).structured_jd_hash
        structured_jd = JDRequirements.model_validate(job.structured_jd)
        if not analysis_identity_is_current(
            analysis,
            resume_hash=evidence_hashes[0],
            experience_bank_hash=evidence_hashes[1],
            structured_jd_hash=jd_hash,
            matcher_model=active_matcher_model(self.settings),
            enforce_matcher_version=(
                structured_jd.requirement_taxonomy_version == "v2"
            ),
        ) or analysis.match_score is None:
            return None, None
        return (
            canonical_hash(
                {
                    "id": analysis.id,
                    "score": analysis.match_score,
                    "recommendation": analysis.recommendation,
                    "requirement_matches": analysis.requirement_matches,
                    "updated_at": analysis.updated_at.isoformat(),
                }
            ),
            analysis,
        )

    def _evidence_hashes(self, profile: UserProfile) -> tuple[str, str] | None:
        try:
            evidence = self.evidence_builder.build(profile)
            return evidence.resume_hash, evidence.experience_bank_hash
        except ValueError:
            return None

    @staticmethod
    def _candidate_hash(profile: UserProfile) -> str:
        facts = []
        for experience in profile.experiences:
            for fact in experience.facts:
                if fact.source_type == "resume" or (
                    fact.source_type == "manual" and fact.confirmed
                ):
                    facts.append(
                        {
                            "id": fact.id,
                            "text": fact.text,
                            "source_type": fact.source_type,
                            "confirmed": fact.confirmed,
                        }
                    )
        return canonical_hash(
            {
                "resume": profile.resume.structured_profile if profile.resume else None,
                "facts": sorted(facts, key=lambda item: item["id"]),
                "preferred_location": profile.preferred_location,
            }
        )

    @staticmethod
    def _target_roles_hash(profile: UserProfile) -> str:
        return canonical_hash(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "priority": item.priority,
                    "auto_role_family": item.auto_role_family,
                    "role_family_override": item.role_family_override,
                    "effective_role_family": item.role_family,
                }
                for item in sorted(profile.target_roles, key=lambda role: role.id)
            ]
        )

    @staticmethod
    def _job_hash(job: Job) -> str:
        relevant_metadata = {
            key: (job.source_metadata or {}).get(key)
            for key in ("job_category", "job_function", "job_subject")
        }
        return canonical_hash(
            {
                "role": job.role,
                "location": job.location,
                "recruitment_type": job.recruitment_type,
                "structured_jd": JDRequirements.model_validate(job.structured_jd).model_dump(
                    mode="json"
                ),
                "source_metadata": relevant_metadata,
            }
        )

    @staticmethod
    def _location_mismatch(preferred: str | None, actual: str | None) -> bool:
        if not preferred or not actual:
            return False
        aliases = {
            "beijing": "北京",
            "北京": "北京",
            "shanghai": "上海",
            "上海": "上海",
            "shenzhen": "深圳",
            "深圳": "深圳",
            "sydney": "sydney",
        }

        def normalize(value: str) -> str:
            lowered = value.casefold()
            for marker, canonical in aliases.items():
                if marker in lowered:
                    return canonical
            return " ".join(lowered.split())

        return normalize(preferred) not in normalize(actual) and normalize(actual) not in normalize(
            preferred
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None
