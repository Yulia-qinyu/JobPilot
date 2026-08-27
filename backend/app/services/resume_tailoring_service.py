from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import JobAnalysis, ResumeTailoring
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.resume_tailoring_repository import ResumeTailoringRepository
from app.schemas.analysis import ResumeProfile
from app.schemas.resume_tailoring import (
    BulletValidation,
    ResumeTailoringRead,
    ResumeTailoringState,
    TailoredBullet,
    TailoredDraft,
    TailoredDraftPatch,
    TailoredExperience,
    TailoringPlan,
    TailoringPlanPatch,
)
from app.services.activity_service import ActivityService
from app.services.evidence_catalog import EvidenceCatalogBuilder, canonical_hash
from app.services.fit_analysis_service import FitAnalysisService
from app.services.requirement_catalog import RequirementCatalogBuilder
from app.services.resume_bullet_rewriter import ResumeBulletRewriter
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.tailoring_evidence import MeaningfulChangeDetector
from app.services.tailoring_plan_service import TailoringPlanService


class ResumeTailoringError(ValueError):
    code = "TAILORING_INVALID"


class TailoringNotFoundError(ResumeTailoringError):
    code = "TAILORING_NOT_FOUND"


class AnalysisRequiredError(ResumeTailoringError):
    code = "ANALYSIS_REQUIRED"


class AnalysisStaleError(ResumeTailoringError):
    code = "ANALYSIS_STALE"


class TailoringStaleError(ResumeTailoringError):
    code = "TAILORING_STALE"


class PlanNotConfirmedError(ResumeTailoringError):
    code = "PLAN_NOT_CONFIRMED"


class InvalidEvidenceReferenceError(ResumeTailoringError):
    code = "INVALID_EVIDENCE_REFERENCE"


class InvalidRequirementReferenceError(ResumeTailoringError):
    code = "INVALID_REQUIREMENT_REFERENCE"


class UnsupportedClaimError(ResumeTailoringError):
    code = "UNSUPPORTED_CLAIM"


class ResumeTailoringService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.repo = ResumeTailoringRepository(db)
        self.job_repo = JobRepository(db)
        self.analysis_repo = JobAnalysisRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.evidence_builder = EvidenceCatalogBuilder()
        self.requirement_builder = RequirementCatalogBuilder()
        self.plan_service = TailoringPlanService()

    def get_state(self, job_id: int) -> ResumeTailoringState:
        job = self._job(job_id)
        analysis = self.analysis_repo.get_for_job(job_id)
        if analysis is None:
            return ResumeTailoringState(tailoring=None, prerequisite="AnalysisRequired")
        if FitAnalysisService(self.db, self.settings).get_state(job_id).is_stale:
            stored = self.repo.get_for_job(job_id)
            return ResumeTailoringState(
                tailoring=self._read(stored, job, analysis) if stored else None,
                prerequisite="AnalysisStale",
            )
        stored = self.repo.get_for_job(job_id)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis) if stored else None,
            prerequisite="Ready",
        )

    def create_plan(self, job_id: int) -> ResumeTailoringState:
        job, analysis, profile, evidence = self._prerequisites(job_id)
        plan = self.plan_service.build(profile, analysis, evidence)
        hashes = self._hashes(job, analysis, evidence)
        stored = self.repo.get_for_job(job_id)
        values = {
            "source_resume_id": profile.resume.id,
            "status": "PlanReady",
            "tailoring_plan": plan.model_dump(mode="json"),
            "generated_draft": {},
            "user_edited_draft": None,
            "validation_results": {},
            "plan_confirmed_at": None,
            "accepted_at": None,
            **hashes,
            "plan_hash": canonical_hash(plan.model_dump(mode="json")),
        }
        if stored is None:
            stored = self.repo.add(ResumeTailoring(job_id=job_id, generation_count=0, **values))
        else:
            for field, value in values.items():
                setattr(stored, field, value)
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def patch_plan(self, job_id: int, payload: TailoringPlanPatch) -> ResumeTailoringState:
        job, analysis, _profile, _evidence = self._prerequisites(job_id)
        stored = self._stored(job_id)
        self._assert_fresh(stored, job, analysis)
        plan = TailoringPlan.model_validate(stored.tailoring_plan)
        by_id = {
            item.plan_item_id: item
            for experience in plan.experiences
            for item in experience.bullet_items
        }
        if len({item.plan_item_id for item in payload.items}) != len(payload.items):
            raise InvalidEvidenceReferenceError("Duplicate plan item IDs.")
        for patch in payload.items:
            item = by_id.get(patch.plan_item_id)
            if item is None:
                raise InvalidEvidenceReferenceError("Unknown plan item ID.")
            if patch.action == "Add":
                evidence = next(
                    (
                        value
                        for value in plan.evidence
                        if value.catalog_id in item.allowed_evidence_ids
                    ),
                    None,
                )
                if evidence is None or evidence.source_type != "manual_confirmed":
                    raise InvalidEvidenceReferenceError("Add requires confirmed manual evidence.")
            item.effective_action = patch.action
            item.omit_confirmed = patch.action == "Omit" and patch.omit_confirmed
            if patch.action == "Omit" and not patch.omit_confirmed:
                item.effective_action = "Keep"
        if payload.section_order is not None:
            allowed_sections = {"work_experience", "projects", "education", "skills"}
            if set(payload.section_order) != allowed_sections or len(payload.section_order) != 4:
                raise ResumeTailoringError("Invalid section order.")
            plan.section_order = payload.section_order
        plan.confirmed = payload.confirmed
        stored.tailoring_plan = plan.model_dump(mode="json")
        stored.plan_hash = canonical_hash(stored.tailoring_plan)
        stored.plan_confirmed_at = datetime.now(UTC) if payload.confirmed else None
        stored.status = "PlanReady"
        stored.generated_draft = {}
        stored.user_edited_draft = None
        stored.validation_results = {}
        stored.accepted_at = None
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def generate_draft(
        self,
        job_id: int,
        rewriter: ResumeBulletRewriter,
        semantic_validator: ResumeClaimValidator,
    ) -> ResumeTailoringState:
        job, analysis, profile, _evidence = self._prerequisites(job_id)
        stored = self._stored(job_id)
        self._assert_fresh(stored, job, analysis)
        plan = TailoringPlan.model_validate(stored.tailoring_plan)
        if not plan.confirmed:
            raise PlanNotConfirmedError("Tailoring plan must be confirmed.")
        output = rewriter.generate(plan)
        generation_metrics = self._client_metrics(rewriter.client)
        generated = self._normalize_generation(output, plan, profile, semantic_validator)
        semantic = semantic_validator.semantic_validate(
            [
                bullet
                for exp in generated.experiences
                for bullet in exp.bullets
                if bullet.state == "Unverified"
            ],
            plan,
        )
        validation_metrics = self._client_metrics(semantic_validator.client)
        self._apply_semantic(generated, semantic.results, plan=plan)
        stored.generated_draft = generated.model_dump(mode="json")
        stored.user_edited_draft = None
        stored.validation_results = {
            **self._validation_summary(generated),
            "generation_calls": 1,
            "validation_calls": 1,
            "generation_metrics": generation_metrics,
            "validation_metrics": validation_metrics,
        }
        stored.status = "DraftReady" if self._all_valid(generated) else "ValidationFailed"
        stored.generator_model = rewriter.client.model
        stored.generator_prompt_version = rewriter.PROMPT_VERSION
        stored.generator_schema_version = rewriter.SCHEMA_VERSION
        stored.validator_model = (
            semantic_validator.client.model if semantic_validator.client else None
        )
        stored.validator_prompt_version = semantic_validator.PROMPT_VERSION
        stored.validator_schema_version = semantic_validator.SCHEMA_VERSION
        stored.guardrail_version = semantic_validator.GUARDRAIL_VERSION
        stored.generation_count += 1
        stored.accepted_at = None
        ActivityService(self.db).record(
            "resume_tailored",
            job_id=job_id,
            metadata={"generation_count": stored.generation_count},
        )
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def edit_draft(self, job_id: int, payload: TailoredDraftPatch) -> ResumeTailoringState:
        job, analysis, profile, _evidence = self._prerequisites(job_id)
        stored = self._stored(job_id)
        self._assert_fresh(stored, job, analysis)
        if not stored.generated_draft:
            raise ResumeTailoringError("No generated draft exists.")
        draft = TailoredDraft.model_validate(stored.user_edited_draft or stored.generated_draft)
        plan = TailoringPlan.model_validate(stored.tailoring_plan)
        plan_items = {
            item.plan_item_id: item for exp in plan.experiences for item in exp.bullet_items
        }
        bullets = {item.plan_item_id: item for exp in draft.experiences for item in exp.bullets}
        if len({item.plan_item_id for item in payload.items}) != len(payload.items):
            raise InvalidEvidenceReferenceError("Duplicate draft item IDs.")
        candidate_skills = ResumeProfile.model_validate(profile.resume.structured_profile).skills
        guard = ResumeClaimValidator()
        for edit in payload.items:
            bullet = bullets.get(edit.plan_item_id)
            plan_item = plan_items.get(edit.plan_item_id)
            if bullet is None or plan_item is None:
                raise InvalidEvidenceReferenceError("Unknown draft item ID.")
            if edit.keep_original:
                bullet.tailored_text = bullet.original_text
                bullet.effective_text = bullet.original_text
                bullet.state = "KeptOriginal"
                bullet.change_kind = "ModelKeep"
                bullet.validation = self._valid_original()
                continue
            result = guard.deterministic(
                edit.text,
                self._evidence_texts(plan, bullet.evidence_source_ids),
                candidate_skills,
                plan_item.context_metadata,
            ).validation
            bullet.tailored_text = edit.text
            bullet.effective_text = bullet.original_text
            bullet.validation = result
            bullet.state = "Unverified" if not result.violations else "FallbackOriginal"
            bullet.change_kind = (
                "MeaningfulRewrite" if not result.violations else "FallbackOriginal"
            )
        stored.user_edited_draft = draft.model_dump(mode="json")
        stored.status = (
            "PendingValidation"
            if any(bullet.state == "Unverified" for bullet in bullets.values())
            else "ValidationFailed"
        )
        stored.validation_results = self._validation_summary(draft)
        stored.accepted_at = None
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def validate_edits(
        self, job_id: int, semantic_validator: ResumeClaimValidator
    ) -> ResumeTailoringState:
        job, analysis, _profile, _evidence = self._prerequisites(job_id)
        stored = self._stored(job_id)
        self._assert_fresh(stored, job, analysis)
        if stored.user_edited_draft is None:
            raise ResumeTailoringError("No user edits require validation.")
        draft = TailoredDraft.model_validate(stored.user_edited_draft)
        pending = [
            bullet
            for exp in draft.experiences
            for bullet in exp.bullets
            if bullet.state == "Unverified"
        ]
        if pending:
            plan = TailoringPlan.model_validate(stored.tailoring_plan)
            results = semantic_validator.semantic_validate(pending, plan)
            self._apply_semantic(
                draft,
                results.results,
                expected_ids={item.plan_item_id for item in pending},
                plan=plan,
            )
        stored.user_edited_draft = draft.model_dump(mode="json")
        stored.validation_results = self._validation_summary(draft)
        stored.status = "Edited" if self._all_valid(draft) else "ValidationFailed"
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def accept(self, job_id: int) -> ResumeTailoringState:
        job, analysis, _profile, _evidence = self._prerequisites(job_id)
        stored = self._stored(job_id)
        self._assert_fresh(stored, job, analysis)
        draft = TailoredDraft.model_validate(stored.user_edited_draft or stored.generated_draft)
        if not self._all_valid(draft):
            raise UnsupportedClaimError(
                "Every selected bullet must be validated before acceptance."
            )
        stored.status = "Accepted"
        stored.accepted_at = datetime.now(UTC)
        self.repo.commit()
        self.repo.refresh(stored)
        return ResumeTailoringState(
            tailoring=self._read(stored, job, analysis), prerequisite="Ready"
        )

    def _normalize_generation(self, output, plan, profile, validator) -> TailoredDraft:
        requested = {
            item.plan_item_id: item
            for exp in plan.experiences
            for item in exp.bullet_items
            if item.effective_action in {"Rewrite", "Add"}
        }
        returned_ids = [item.plan_item_id for item in output.bullets]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != set(requested):
            raise InvalidEvidenceReferenceError(
                "Generation must return every planned item exactly once."
            )
        segments = {item.segment_id: item for item in plan.evidence_segments}
        requirements = {item.requirement_id for item in plan.relevant_requirements}
        output_by_id = {item.plan_item_id: item for item in output.bullets}
        candidate_skills = ResumeProfile.model_validate(profile.resume.structured_profile).skills
        experiences = []
        for exp in plan.experiences:
            bullets = []
            ordered_items = sorted(
                exp.bullet_items,
                key=lambda item: item.effective_action == "DeEmphasize",
            )
            for item in ordered_items:
                if item.effective_action == "Omit" and item.omit_confirmed:
                    continue
                if item.effective_action in {"Rewrite", "Add"}:
                    generated = output_by_id[item.plan_item_id]
                    self._validate_generated_references(
                        item, generated.evidence_source_ids, segments
                    )
                    if (
                        not set(generated.requirement_ids) <= set(item.target_requirement_ids)
                        or not set(generated.requirement_ids) <= requirements
                    ):
                        raise InvalidRequirementReferenceError(
                            "Generated requirement is outside the item allowlist."
                        )
                    if generated.action == "Keep":
                        keep_action = "Add" if item.effective_action == "Add" else "Keep"
                        bullets.append(
                            TailoredBullet(
                                plan_item_id=item.plan_item_id,
                                experience_id=exp.experience_id,
                                original_text=item.original_text,
                                tailored_text=item.original_text,
                                effective_text=item.original_text,
                                action=keep_action,
                                evidence_source_ids=generated.evidence_source_ids,
                                requirement_ids=generated.requirement_ids,
                                change_summary=(
                                    generated.change_summary or "原内容已经较适合该岗位，建议保留。"
                                ),
                                validation=self._valid_original(),
                                state="KeptOriginal",
                                change_kind=(
                                    "AddedConfirmedFact"
                                    if item.effective_action == "Add"
                                    else "ModelKeep"
                                ),
                            )
                        )
                        continue
                    if (
                        item.effective_action != "Add"
                        and MeaningfulChangeDetector.is_formatting_only(
                            item.original_text,
                            generated.rewritten_text,
                            item.context_metadata,
                        )
                    ):
                        bullets.append(
                            TailoredBullet(
                                plan_item_id=item.plan_item_id,
                                experience_id=exp.experience_id,
                                original_text=item.original_text,
                                tailored_text=generated.rewritten_text,
                                effective_text=item.original_text,
                                action="Keep",
                                evidence_source_ids=generated.evidence_source_ids,
                                requirement_ids=generated.requirement_ids,
                                change_summary="未发现有价值的实质改写，已保留原文。",
                                validation=self._valid_original(),
                                state="KeptOriginal",
                                change_kind="FormattingOnlyKeep",
                            )
                        )
                        continue
                    validation = validator.deterministic(
                        generated.rewritten_text,
                        self._evidence_texts(plan, generated.evidence_source_ids),
                        candidate_skills,
                        item.context_metadata,
                    ).validation
                    safe = not validation.violations
                    bullets.append(
                        TailoredBullet(
                            plan_item_id=item.plan_item_id,
                            experience_id=exp.experience_id,
                            original_text=item.original_text,
                            tailored_text=generated.rewritten_text,
                            effective_text=item.original_text,
                            action=item.effective_action,
                            evidence_source_ids=generated.evidence_source_ids,
                            requirement_ids=generated.requirement_ids,
                            change_summary=generated.change_summary,
                            validation=validation,
                            state="Unverified" if safe else "FallbackOriginal",
                            change_kind=(
                                "AddedConfirmedFact"
                                if item.effective_action == "Add" and safe
                                else "MeaningfulRewrite"
                                if safe
                                else "FallbackOriginal"
                            ),
                        )
                    )
                else:
                    bullets.append(
                        TailoredBullet(
                            plan_item_id=item.plan_item_id,
                            experience_id=exp.experience_id,
                            original_text=item.original_text,
                            tailored_text=item.original_text,
                            effective_text=item.original_text,
                            action=item.effective_action,
                            evidence_source_ids=item.allowed_evidence_ids,
                            requirement_ids=item.target_requirement_ids,
                            change_summary="保留原始事实。",
                            validation=self._valid_original(),
                            state="KeptOriginal",
                            change_kind="PlanKeep",
                        )
                    )
            experiences.append(
                TailoredExperience(
                    experience_id=exp.experience_id,
                    organization=exp.organization,
                    title=exp.title,
                    date_range=exp.date_range,
                    bullets=bullets,
                )
            )
        profile_data = ResumeProfile.model_validate(profile.resume.structured_profile)
        return TailoredDraft(
            summary=" ".join(output.summary.split()),
            education=[item.model_dump(mode="json") for item in profile_data.education],
            skills=plan.skills_to_include,
            experiences=experiences,
        )

    def _apply_semantic(self, draft, results, expected_ids=None, plan=None) -> None:
        bullets = {item.plan_item_id: item for exp in draft.experiences for item in exp.bullets}
        plan_items = (
            {
                item.plan_item_id: item
                for experience in plan.experiences
                for item in experience.bullet_items
            }
            if plan is not None
            else {}
        )
        expected = expected_ids or {
            item.plan_item_id for item in bullets.values() if item.state == "Unverified"
        }
        returned = [item.plan_item_id for item in results]
        if len(returned) != len(set(returned)) or set(returned) != expected:
            raise InvalidEvidenceReferenceError(
                "Semantic validation returned invalid plan item IDs."
            )
        for result in results:
            bullet = bullets[result.plan_item_id]
            metadata = (
                plan_items[result.plan_item_id].context_metadata
                if result.plan_item_id in plan_items
                else None
            )
            unsupported_spans = [
                span
                for span in result.unsupported_spans
                if not self._metadata_supports_span(span, metadata)
            ]
            invalid_spans = [span for span in unsupported_spans if span not in bullet.tailored_text]
            if invalid_spans:
                bullet.validation.semantic_supported = False
                bullet.validation.violations.append(
                    "语义验证返回了无法映射到候选内容的 unsupported span。"
                )
            else:
                bullet.validation.semantic_supported = not unsupported_spans
                bullet.validation.violations.extend(unsupported_spans)
            deterministic_valid = all(
                (
                    bullet.validation.references_valid,
                    bullet.validation.numbers_valid,
                    bullet.validation.skills_valid,
                    bullet.validation.ownership_valid,
                    bullet.validation.entities_valid,
                )
            )
            if bullet.validation.semantic_supported and deterministic_valid:
                bullet.effective_text = bullet.tailored_text
                bullet.state = "Validated"
            else:
                bullet.effective_text = bullet.original_text
                bullet.state = "FallbackOriginal"
                bullet.change_kind = "FallbackOriginal"

    def _prerequisites(self, job_id):
        job = self._job(job_id)
        analysis = self.analysis_repo.get_for_job(job_id)
        if analysis is None:
            raise AnalysisRequiredError("A valid Fit Analysis is required.")
        if FitAnalysisService(self.db, self.settings).get_state(job_id).is_stale:
            raise AnalysisStaleError("Fit Analysis is stale.")
        profile = self.profile_repo.get_full_profile()
        evidence = self.evidence_builder.build(profile)
        return job, analysis, profile, evidence

    def _hashes(self, job, analysis, evidence):
        return {
            "resume_hash": evidence.resume_hash,
            "experience_bank_hash": evidence.experience_bank_hash,
            "structured_jd_hash": self.requirement_builder.build(
                job.structured_jd
            ).structured_jd_hash,
            "analysis_hash": self._analysis_hash(analysis),
        }

    def _assert_fresh(self, stored, job, analysis):
        profile = self.profile_repo.get_full_profile()
        evidence = self.evidence_builder.build(profile)
        current = self._hashes(job, analysis, evidence)
        plan_version = stored.tailoring_plan.get("plan_version", "tailoring-plan-v1")
        if plan_version != TailoringPlanService.PLAN_VERSION or any(
            getattr(stored, key) != value for key, value in current.items()
        ):
            raise TailoringStaleError("Resume tailoring inputs have changed.")

    def _read(self, stored, job, analysis):
        current = self._hashes(
            job, analysis, self.evidence_builder.build(self.profile_repo.get_full_profile())
        )
        stale = [key for key, value in current.items() if getattr(stored, key) != value]
        if (
            stored.tailoring_plan.get("plan_version", "tailoring-plan-v1")
            != TailoringPlanService.PLAN_VERSION
        ):
            stale.append("tailoring_engine_version")
        value = ResumeTailoringRead.model_validate(stored)
        return value.model_copy(update={"is_stale": bool(stale), "stale_reasons": stale})

    def _job(self, job_id):
        job = self.job_repo.get(job_id)
        if job is None:
            raise TailoringNotFoundError("Job not found.")
        return job

    def _stored(self, job_id):
        stored = self.repo.get_for_job(job_id)
        if stored is None:
            raise TailoringNotFoundError("Resume tailoring not found.")
        return stored

    @staticmethod
    def _analysis_hash(analysis: JobAnalysis) -> str:
        return canonical_hash(
            {
                "requirement_matches": analysis.requirement_matches,
                "recommendation": analysis.recommendation,
                "match_score": analysis.match_score,
            }
        )

    @staticmethod
    def _valid_original() -> BulletValidation:
        return BulletValidation(
            references_valid=True,
            numbers_valid=True,
            skills_valid=True,
            ownership_valid=True,
            entities_valid=True,
            semantic_supported=True,
        )

    @staticmethod
    def _all_valid(draft: TailoredDraft) -> bool:
        return all(
            bullet.state in {"Validated", "KeptOriginal"}
            for experience in draft.experiences
            for bullet in experience.bullets
        )

    @staticmethod
    def _validation_summary(draft: TailoredDraft) -> dict:
        bullets = [bullet for experience in draft.experiences for bullet in experience.bullets]
        return {
            "total": len(bullets),
            "validated": sum(item.state == "Validated" for item in bullets),
            "kept_original": sum(item.state == "KeptOriginal" for item in bullets),
            "fallback_original": sum(item.state == "FallbackOriginal" for item in bullets),
            "unverified": sum(item.state == "Unverified" for item in bullets),
            "meaningful_rewrite": sum(
                item.change_kind in {"MeaningfulRewrite", "AddedConfirmedFact"}
                and item.state == "Validated"
                for item in bullets
            ),
            "model_keep": sum(item.change_kind == "ModelKeep" for item in bullets),
            "formatting_only_keep": sum(
                item.change_kind == "FormattingOnlyKeep" for item in bullets
            ),
        }

    @staticmethod
    def _evidence_texts(plan: TailoringPlan, source_ids: list[str]) -> list[str]:
        evidence = {item.catalog_id: item.text for item in plan.evidence}
        segments = {item.segment_id: item.text for item in plan.evidence_segments}
        values = []
        for source_id in source_ids:
            if source_id in segments:
                values.append(segments[source_id])
            elif source_id in evidence:
                values.append(evidence[source_id])
            else:
                raise InvalidEvidenceReferenceError("Unknown evidence source ID.")
        return values

    @staticmethod
    def _validate_generated_references(item, source_ids, segments) -> None:
        allowed_references = set(item.allowed_evidence_ids) | set(item.allowed_segment_ids)
        if not source_ids or not set(source_ids) <= allowed_references:
            raise InvalidEvidenceReferenceError("Generated evidence is outside the item allowlist.")
        for source_id in source_ids:
            if (
                source_id in segments
                and segments[source_id].parent_source_id not in item.allowed_evidence_ids
            ):
                raise InvalidEvidenceReferenceError(
                    "Generated segment belongs to another evidence source."
                )

    @staticmethod
    def _metadata_supports_span(span, metadata) -> bool:
        if metadata is None:
            return False
        direct = span.strip()
        direct = direct.removeprefix("担任").removeprefix("任职为").strip("，,。.;；:： ")
        normalized = MeaningfulChangeDetector.normalize(direct)
        if not normalized:
            return False
        if any(
            normalized == MeaningfulChangeDetector.normalize(value)
            or normalized in MeaningfulChangeDetector.normalize(value)
            for value in (
                metadata.experience_title,
                metadata.organization,
                metadata.project_name,
                metadata.date_range,
            )
            if value
        ):
            return True
        title = MeaningfulChangeDetector.normalize(metadata.experience_title)
        title_aliases = (
            {"productowner", "产品负责人"},
            {"productmanager", "产品经理"},
            {"projectmanager", "项目经理"},
        )
        return any(
            normalized in aliases and any(alias in title for alias in aliases)
            for aliases in title_aliases
        )

    @staticmethod
    def _client_metrics(client: object | None) -> dict:
        metrics = getattr(client, "last_call_metrics", {}) if client is not None else {}
        return dict(metrics) if isinstance(metrics, dict) else {}
