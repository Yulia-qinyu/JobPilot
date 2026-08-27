import logging
from time import perf_counter

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import JobAnalysis
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import JDRequirements
from app.schemas.fit_analysis import (
    FitAnalysisOutput,
    FitAnalysisPreview,
    FitAnalysisRead,
    FitAnalysisState,
    FitGap,
    FitStrength,
    PreparationItem,
    RequirementMatch,
)
from app.services.activity_service import ActivityService
from app.services.candidate_requirement_evidence import CandidateRequirementEvidenceNormalizer
from app.services.evidence_catalog import EvidenceCatalog, EvidenceCatalogBuilder
from app.services.hard_requirements import validate_hard_requirement
from app.services.match_score import MatchScoreService, NoScorableRequirementsError
from app.services.preview_analysis_store import new_artifact, preview_analysis_store
from app.services.requirement_catalog import RequirementCatalog, RequirementCatalogBuilder
from app.services.requirement_matcher import RequirementMatcher

logger = logging.getLogger(__name__)


class FitAnalysisError(ValueError):
    pass


class FitAnalysisNotFoundError(FitAnalysisError):
    pass


class FitAnalysisPrerequisiteError(FitAnalysisError):
    pass


class FitAnalysisNormalizationError(FitAnalysisError):
    pass


class FitAnalysisService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.job_repo = JobRepository(db)
        self.analysis_repo = JobAnalysisRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.evidence_builder = EvidenceCatalogBuilder()
        self.requirement_builder = RequirementCatalogBuilder()
        self.score_service = MatchScoreService()
        self.candidate_requirement_normalizer = CandidateRequirementEvidenceNormalizer()

    def get_state(self, job_id: int) -> FitAnalysisState:
        job = self.job_repo.get(job_id)
        if job is None:
            raise FitAnalysisNotFoundError("Job not found.")
        stored = self.analysis_repo.get_for_job(job_id)
        if stored is None:
            return FitAnalysisState(analysis=None)

        stale_reasons: list[str] = []
        try:
            profile = self.profile_repo.get_full_profile()
            evidence = self.evidence_builder.build(profile)
            if stored.resume_hash != evidence.resume_hash:
                stale_reasons.append("resume")
            if stored.experience_bank_hash != evidence.experience_bank_hash:
                stale_reasons.append("experience_bank")
        except ValueError:
            stale_reasons.append("resume")
        jd_hash = self.requirement_builder.build(job.structured_jd).structured_jd_hash
        if stored.structured_jd_hash != jd_hash:
            stale_reasons.append("job_description")
        return FitAnalysisState(
            analysis=FitAnalysisRead.model_validate(stored),
            is_stale=bool(stale_reasons),
            stale_reasons=stale_reasons,
        )

    def analyze(self, job_id: int, matcher: RequirementMatcher) -> FitAnalysisState:
        started_at = perf_counter()
        job = self.job_repo.get(job_id)
        if job is None:
            raise FitAnalysisNotFoundError("Job not found.")
        profile = self.profile_repo.get_full_profile()
        try:
            evidence = self.evidence_builder.build(profile)
        except ValueError as exc:
            raise FitAnalysisPrerequisiteError(str(exc)) from exc
        requirements = self.requirement_builder.build(job.structured_jd)
        if not requirements.requirements:
            raise FitAnalysisPrerequisiteError("The saved JD has no scorable requirements.")

        logger.info(
            "Fit analysis started stage=requirement_matcher job_id=%s model=%s "
            "requirement_count=%s evidence_count=%s",
            job_id,
            matcher.client.model,
            len(requirements.requirements),
            len(evidence.sources),
        )
        output = matcher.analyze(requirements, evidence)
        (
            matches,
            unsupported_evidence_count,
            hard_downgrade_count,
            deterministic_adjustment_count,
        ) = self._normalize_matches(output, requirements, evidence)
        try:
            score = self.score_service.score(matches)
        except NoScorableRequirementsError as exc:
            raise FitAnalysisPrerequisiteError(str(exc)) from exc
        recommendation = self.score_service.recommendation(score, matches)
        preparation = self._normalize_preparation(output, requirements)
        strengths = self._derive_strengths(matches)
        gaps = self._derive_gaps(matches, preparation)
        stored = self._persist(
            job=job,
            matcher=matcher,
            output=output,
            summary=self._final_summary(
                output.summary, matches, deterministic_adjustment_count
            ),
            evidence=evidence,
            requirements=requirements,
            matches=matches,
            score=score,
            recommendation=recommendation,
            preparation=preparation,
            strengths=strengths,
            gaps=gaps,
        )
        logger.info(
            "Fit analysis completed stage=fit_analysis job_id=%s elapsed_seconds=%.3f "
            "model=%s requirement_count=%s evidence_count=%s unsupported_evidence_count=%s "
            "hard_classification_downgrades=%s claude_api_calls=1 status=success",
            job_id,
            perf_counter() - started_at,
            matcher.client.model,
            len(matches),
            len(evidence.sources),
            unsupported_evidence_count,
            hard_downgrade_count,
        )
        return FitAnalysisState(analysis=FitAnalysisRead.model_validate(stored))

    def analyze_preview(
        self, structured_jd: JDRequirements, matcher: RequirementMatcher
    ) -> FitAnalysisPreview:
        """Analyze a JD against verified candidate evidence without creating a Job."""
        profile = self.profile_repo.get_full_profile()
        try:
            evidence = self.evidence_builder.build(profile)
        except ValueError as exc:
            raise FitAnalysisPrerequisiteError(str(exc)) from exc
        requirements = self.requirement_builder.build(structured_jd.model_dump(mode="json"))
        if not requirements.requirements:
            raise FitAnalysisPrerequisiteError("The saved JD has no scorable requirements.")
        output = matcher.analyze(requirements, evidence)
        matches, _, _, deterministic_adjustment_count = self._normalize_matches(
            output, requirements, evidence
        )
        try:
            score = self.score_service.score(matches)
        except NoScorableRequirementsError as exc:
            raise FitAnalysisPrerequisiteError(str(exc)) from exc
        preparation = self._normalize_preparation(output, requirements)
        preview = FitAnalysisPreview(
            match_score=score,
            recommendation=self.score_service.recommendation(score, matches),
            summary=self._final_summary(
                output.summary, matches, deterministic_adjustment_count
            ),
            requirement_matches=matches,
            strengths=self._derive_strengths(matches),
            gaps=self._derive_gaps(matches, preparation),
            suggested_preparation=preparation,
        )
        artifact = new_artifact(
            analysis=preview,
            resume_hash=evidence.resume_hash,
            experience_bank_hash=evidence.experience_bank_hash,
            structured_jd_hash=requirements.structured_jd_hash,
            matcher_model=matcher.client.model,
            matcher_prompt_version=matcher.PROMPT_VERSION,
            matcher_schema_version=matcher.SCHEMA_VERSION,
        )
        preview_analysis_store.put(artifact)
        return preview.model_copy(update={
            "artifact_token": artifact.token,
            "artifact_expires_at": artifact.expires_at,
        })

    def promote_preview(self, job, token: str) -> JobAnalysis | None:
        artifact = preview_analysis_store.get(token)
        if artifact is None:
            return None
        try:
            profile = self.profile_repo.get_full_profile()
            evidence = self.evidence_builder.build(profile)
            requirements = self.requirement_builder.build(job.structured_jd)
        except ValueError:
            return None
        if (
            artifact.resume_hash != evidence.resume_hash
            or artifact.experience_bank_hash != evidence.experience_bank_hash
            or artifact.structured_jd_hash != requirements.structured_jd_hash
            or artifact.matcher_prompt_version != RequirementMatcher.PROMPT_VERSION
            or artifact.matcher_schema_version != RequirementMatcher.SCHEMA_VERSION
            or artifact.matcher_model != self.settings.claude_model
        ):
            return None
        analysis = artifact.analysis
        stored = JobAnalysis(
            job_id=job.id,
            resume_hash=artifact.resume_hash,
            experience_bank_hash=artifact.experience_bank_hash,
            structured_jd_hash=artifact.structured_jd_hash,
            matcher_model=artifact.matcher_model,
            matcher_prompt_version=artifact.matcher_prompt_version,
            matcher_schema_version=artifact.matcher_schema_version,
            match_score=analysis.match_score,
            recommendation=analysis.recommendation,
            summary=analysis.summary,
            requirement_matches=[item.model_dump(mode="json") for item in analysis.requirement_matches],
            strengths=[item.model_dump(mode="json") for item in analysis.strengths],
            gaps=[item.model_dump(mode="json") for item in analysis.gaps],
            suggested_preparation=[item.model_dump(mode="json") for item in analysis.suggested_preparation],
        )
        self.db.add(stored)
        job.match_score = analysis.match_score
        job.recommendation = analysis.recommendation
        preview_analysis_store.consume(token)
        return stored

    def _normalize_matches(
        self,
        output: FitAnalysisOutput,
        requirements: RequirementCatalog,
        evidence: EvidenceCatalog,
    ) -> tuple[list[RequirementMatch], int, int, int]:
        expected_ids = set(requirements.by_id)
        returned_ids = [item.requirement_id for item in output.requirement_matches]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != expected_ids:
            raise FitAnalysisNormalizationError(
                "Claude did not return exactly one match for every requirement."
            )

        evidence_by_id = evidence.by_catalog_id
        unsupported_count = 0
        hard_downgrade_count = 0
        deterministic_adjustment_count = 0
        normalized: list[RequirementMatch] = []
        for item in output.requirement_matches:
            requirement = requirements.by_id[item.requirement_id]
            cited = []
            seen_evidence: set[str] = set()
            for source_id in item.evidence_source_ids:
                if source_id in seen_evidence:
                    continue
                seen_evidence.add(source_id)
                source = evidence_by_id.get(source_id)
                if source is None:
                    unsupported_count += 1
                    continue
                cited.append(source)

            supported_hard, hard_category = validate_hard_requirement(
                requirement, item.is_hard_requirement
            )
            if item.is_hard_requirement and not supported_hard:
                hard_downgrade_count += 1
            importance = "Critical" if supported_hard else item.importance
            match_status = item.match_status
            reason = " ".join(item.reason.split())
            confidence = item.confidence
            if match_status == "Missing":
                cited = []
            elif not cited:
                match_status = "Missing"
                confidence = "Low"
            if match_status == "Missing":
                reason = "当前已验证的简历与经历事实中，暂未找到支持该要求的证据。"

            identity_normalization = self.candidate_requirement_normalizer.normalize(
                requirement.text,
                requirement.context,
                match_status,
                reason,
                confidence,
                cited,
                evidence_by_id,
            )
            if identity_normalization is not None:
                if (
                    match_status != identity_normalization.match_status
                    or reason != identity_normalization.reason
                    or confidence != identity_normalization.confidence
                    or cited != identity_normalization.evidence_sources
                ):
                    deterministic_adjustment_count += 1
                match_status = identity_normalization.match_status
                reason = identity_normalization.reason
                confidence = identity_normalization.confidence
                cited = identity_normalization.evidence_sources

            normalized.append(
                RequirementMatch(
                    requirement_id=requirement.requirement_id,
                    requirement_text=requirement.text,
                    importance=importance,
                    is_hard_requirement=supported_hard,
                    hard_requirement_category=hard_category,
                    match_status=match_status,
                    reason=reason or "未提供有效匹配说明。",
                    confidence=confidence,
                    evidence_sources=cited,
                )
            )
        return (
            normalized,
            unsupported_count,
            hard_downgrade_count,
            deterministic_adjustment_count,
        )

    @staticmethod
    def _final_summary(
        model_summary: str,
        matches: list[RequirementMatch],
        deterministic_adjustment_count: int,
    ) -> str:
        if deterministic_adjustment_count == 0:
            return " ".join(model_summary.split()) or "已完成岗位要求与经历证据匹配。"
        counts = {
            status: sum(item.match_status == status for item in matches)
            for status in ("Strong", "Partial", "Missing")
        }
        return (
            f"已按最终验证证据完成 {len(matches)} 项岗位要求核验："
            f"{counts['Strong']} 项已匹配，{counts['Partial']} 项部分匹配，"
            f"{counts['Missing']} 项暂无匹配证据。"
        )

    @staticmethod
    def _normalize_preparation(
        output: FitAnalysisOutput, requirements: RequirementCatalog
    ) -> list[PreparationItem]:
        valid_ids = set(requirements.by_id)
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        items: list[PreparationItem] = []
        seen: set[str] = set()
        for item in output.suggested_preparation:
            title = " ".join(item.title.split())
            action = " ".join(item.action.split())
            key = f"{title.casefold()}:{action.casefold()}"
            if not title or not action or key in seen:
                continue
            seen.add(key)
            items.append(
                PreparationItem(
                    title=title,
                    action=action,
                    priority=item.priority,
                    requirement_ids=[
                        requirement_id
                        for requirement_id in dict.fromkeys(item.requirement_ids)
                        if requirement_id in valid_ids
                    ],
                )
            )
        return sorted(items, key=lambda item: priority_order[item.priority])

    @staticmethod
    def _derive_strengths(matches: list[RequirementMatch]) -> list[FitStrength]:
        importance_order = {"Critical": 3, "Important": 2, "Preferred": 1}
        candidates = sorted(
            (item for item in matches if item.match_status == "Strong"),
            key=lambda item: (
                -importance_order[item.importance],
                -int(item.is_hard_requirement),
                item.requirement_text.casefold(),
            ),
        )
        return [
            FitStrength(
                title=item.requirement_text,
                explanation=item.reason,
                requirement_ids=[item.requirement_id],
                evidence=item.evidence_sources,
            )
            for item in candidates[:3]
        ]

    @staticmethod
    def _derive_gaps(
        matches: list[RequirementMatch], preparation: list[PreparationItem]
    ) -> list[FitGap]:
        importance_order = {"Critical": 3, "Important": 2, "Preferred": 1}
        status_order = {"Missing": 2, "Partial": 1, "Strong": 0}
        candidates = sorted(
            (item for item in matches if item.match_status != "Strong"),
            key=lambda item: (
                -int(item.is_hard_requirement and item.match_status == "Missing"),
                -importance_order[item.importance],
                -status_order[item.match_status],
                item.requirement_text.casefold(),
            ),
        )
        gaps: list[FitGap] = []
        seen_titles: set[str] = set()
        for item in candidates:
            normalized_title = " ".join(item.requirement_text.casefold().split())
            if normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            linked_action = next(
                (
                    prep.action
                    for prep in preparation
                    if item.requirement_id in prep.requirement_ids
                ),
                None,
            )
            gaps.append(
                FitGap(
                    title=("关键硬性缺口：" if item.is_hard_requirement else "")
                    + item.requirement_text,
                    severity=FitAnalysisService._gap_severity(item),
                    requirement_id=item.requirement_id,
                    requirement=item.requirement_text,
                    explanation=item.reason,
                    evidence_status="partial" if item.match_status == "Partial" else "none",
                    next_step=linked_action or FitAnalysisService._default_next_step(item),
                    is_hard_requirement=item.is_hard_requirement,
                    hard_requirement_category=item.hard_requirement_category,
                )
            )
            if len(gaps) == 5:
                break
        return gaps

    @staticmethod
    def _gap_severity(item: RequirementMatch) -> str:
        if item.is_hard_requirement or (
            item.importance == "Critical" and item.match_status == "Missing"
        ):
            return "critical"
        if item.importance == "Critical" or (
            item.importance == "Important" and item.match_status == "Missing"
        ):
            return "high"
        return "medium"

    @staticmethod
    def _default_next_step(item: RequirementMatch) -> str:
        if item.hard_requirement_category in {"eligibility", "qualification"}:
            return "先确认是否满足该硬性条件；若不满足，应降低该岗位的投递优先级。"
        if item.hard_requirement_category == "experience":
            return "核对年限要求，并准备能够证明相关深度和可迁移能力的真实案例。"
        if item.match_status == "Partial":
            return "准备更具体的项目案例、个人贡献和结果，补强现有证据。"
        return "优先理解该要求，并准备可验证的实践案例。"

    def _persist(
        self,
        *,
        job,
        matcher: RequirementMatcher,
        output: FitAnalysisOutput,
        summary: str,
        evidence: EvidenceCatalog,
        requirements: RequirementCatalog,
        matches: list[RequirementMatch],
        score: int,
        recommendation: str,
        preparation: list[PreparationItem],
        strengths: list[FitStrength],
        gaps: list[FitGap],
    ) -> JobAnalysis:
        stored = self.analysis_repo.get_for_job(job.id)
        values = {
            "resume_hash": evidence.resume_hash,
            "experience_bank_hash": evidence.experience_bank_hash,
            "structured_jd_hash": requirements.structured_jd_hash,
            "matcher_model": matcher.client.model,
            "matcher_prompt_version": matcher.PROMPT_VERSION,
            "matcher_schema_version": matcher.SCHEMA_VERSION,
            "match_score": score,
            "recommendation": recommendation,
            "summary": summary,
            "requirement_matches": [item.model_dump(mode="json") for item in matches],
            "strengths": [item.model_dump(mode="json") for item in strengths],
            "gaps": [item.model_dump(mode="json") for item in gaps],
            "suggested_preparation": [item.model_dump(mode="json") for item in preparation],
        }
        if stored is None:
            stored = self.analysis_repo.add(JobAnalysis(job_id=job.id, **values))
        else:
            for field, value in values.items():
                setattr(stored, field, value)
        job.match_score = score
        job.recommendation = recommendation
        ActivityService(self.db).record(
            "job_analyzed",
            job_id=job.id,
            metadata={"match_score": score, "source": "analysis"},
        )
        self.analysis_repo.commit()
        self.analysis_repo.refresh(stored)
        return stored
