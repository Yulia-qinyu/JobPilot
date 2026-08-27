from collections import defaultdict
from typing import ClassVar

from app.db.models import JobAnalysis, UserProfile
from app.schemas.analysis import ResumeProfile
from app.schemas.fit_analysis import RequirementMatch
from app.schemas.resume_tailoring import (
    BulletPlanItem,
    ExperiencePlan,
    PlanEvidence,
    PlanRequirement,
    TailoringPlan,
)
from app.services.evidence_catalog import EvidenceCatalog, EvidenceCatalogBuilder
from app.services.tailoring_evidence import TailoringEvidenceSegmenter


class TailoringPlanService:
    PLAN_VERSION = "tailoring-plan-v2"
    IMPORTANCE_WEIGHT: ClassVar[dict[str, float]] = {
        "Critical": 5.0,
        "Important": 3.0,
        "Preferred": 1.0,
    }
    MATCH_VALUE: ClassVar[dict[str, float]] = {
        "Strong": 1.0,
        "Partial": 0.5,
        "Missing": 0.0,
    }

    def build(
        self, profile: UserProfile, analysis: JobAnalysis, evidence: EvidenceCatalog
    ) -> TailoringPlan:
        matches = [RequirementMatch.model_validate(item) for item in analysis.requirement_matches]
        requirements = {
            item.requirement_id: PlanRequirement(
                requirement_id=item.requirement_id,
                text=item.requirement_text,
                importance=item.importance,
                match_status=item.match_status,
            )
            for item in matches
        }
        evidence_by_id = evidence.by_catalog_id
        segmenter = TailoringEvidenceSegmenter()
        claim_text_by_id: dict[str, str] = {}
        segments_by_id = {}
        requirement_ids_by_evidence: dict[str, list[str]] = defaultdict(list)
        scores_by_experience: dict[int, float] = defaultdict(float)
        fact_experience: dict[str, int] = {}
        for experience in profile.experiences:
            for fact in experience.facts:
                fact_experience[str(fact.id)] = experience.id

        for match in matches:
            value = self.IMPORTANCE_WEIGHT[match.importance] * self.MATCH_VALUE[match.match_status]
            for source in match.evidence_sources:
                catalog_id = EvidenceCatalogBuilder.catalog_id(source)
                if catalog_id not in evidence_by_id:
                    continue
                requirement_ids_by_evidence[catalog_id].append(match.requirement_id)
                experience_id = fact_experience.get(source.source_id)
                if experience_id is not None:
                    scores_by_experience[experience_id] += value

        experience_plans: list[ExperiencePlan] = []
        used_evidence_ids: set[str] = set()
        for experience in profile.experiences:
            bullet_items: list[BulletPlanItem] = []
            covered_requirements: set[str] = set()
            for fact in experience.facts:
                provenance = EvidenceCatalogBuilder._eligible_provenance(
                    fact.source_type, fact.confirmed
                )
                if provenance is None:
                    continue
                catalog_id = f"{provenance}:{fact.id}"
                segmented = segmenter.segment(
                    parent_source_id=catalog_id,
                    text=fact.text,
                    experience_title=experience.title,
                    organization=experience.organization,
                    date_range=experience.date_range or "",
                )
                claim_text_by_id[catalog_id] = segmented.claim_text
                segments_by_id[catalog_id] = segmented.segments
                linked = list(dict.fromkeys(requirement_ids_by_evidence.get(catalog_id, [])))
                if fact.source_type == "manual" and not linked:
                    continue
                covered_requirements.update(linked)
                used_evidence_ids.add(catalog_id)
                if linked:
                    if provenance == "manual_confirmed":
                        recommended = "Add"
                        reason = f"新增已确认事实，支持 {len(linked)} 个岗位要求。"
                    elif self._rewrite_worthy(segmented.claim_text, len(linked)):
                        recommended = "Rewrite"
                        reason = f"包含可重排或压缩的信息，支持 {len(linked)} 个岗位要求。"
                    else:
                        recommended = "Keep"
                        reason = f"原内容已直接支持 {len(linked)} 个岗位要求，建议保留。"
                else:
                    recommended = "Keep"
                    reason = "保留主简历中的原始事实。"
                bullet_items.append(
                    BulletPlanItem(
                        plan_item_id=f"experience_{experience.id}_fact_{fact.id}",
                        experience_id=experience.id,
                        source_fact_id=fact.id,
                        original_text=fact.text,
                        recommended_action=recommended,
                        effective_action=recommended,
                        omit_confirmed=False,
                        target_requirement_ids=linked,
                        allowed_evidence_ids=[catalog_id],
                        allowed_segment_ids=[item.segment_id for item in segmented.segments],
                        context_metadata=segmented.context_metadata,
                        reason=reason,
                    )
                )
            score = scores_by_experience[experience.id]
            experience_plans.append(
                ExperiencePlan(
                    experience_id=experience.id,
                    organization=experience.organization,
                    title=experience.title,
                    date_range=experience.date_range or "",
                    emphasis="Highlight" if score > 0 else "Keep",
                    coverage_summary=(
                        f"建议重点突出，覆盖 {len(covered_requirements)} 个岗位要求。"
                        if covered_requirements
                        else "与当前岗位要求没有直接证据映射，默认保留。"
                    ),
                    bullet_items=bullet_items,
                )
            )
        experience_plans.sort(
            key=lambda item: (-scores_by_experience[item.experience_id], item.experience_id)
        )

        supported_ids = {
            item.requirement_id
            for item in matches
            if item.match_status != "Missing" and item.evidence_sources
        }
        unsupported = [
            requirements[item.requirement_id]
            for item in matches
            if item.requirement_id not in supported_ids
        ]
        relevant = [
            requirements[item.requirement_id]
            for item in matches
            if item.requirement_id in supported_ids
        ]
        plan_evidence = [
            PlanEvidence(
                catalog_id=catalog_id,
                source_type=evidence_by_id[catalog_id].source_type,
                source_id=evidence_by_id[catalog_id].source_id,
                text=evidence_by_id[catalog_id].text,
                context=evidence_by_id[catalog_id].context,
            )
            for catalog_id in sorted(used_evidence_ids)
            if catalog_id in evidence_by_id
        ]
        for item in plan_evidence:
            item.text = claim_text_by_id.get(item.catalog_id, item.text)
        evidence_segments = [
            segment
            for catalog_id in sorted(used_evidence_ids)
            for segment in segments_by_id.get(catalog_id, [])
        ]
        structured = ResumeProfile.model_validate(profile.resume.structured_profile)
        requirement_text = " ".join(item.text.casefold() for item in relevant)
        skills = sorted(
            structured.skills,
            key=lambda skill: (
                skill.casefold() not in requirement_text,
                structured.skills.index(skill),
            ),
        )
        return TailoringPlan(
            plan_version=self.PLAN_VERSION,
            relevant_requirements=relevant,
            experiences=experience_plans,
            evidence=plan_evidence,
            evidence_segments=evidence_segments,
            section_order=["work_experience", "projects", "education", "skills"],
            skills_to_include=skills,
            unsupported_requirements=unsupported,
        )

    @staticmethod
    def _rewrite_worthy(text: str, requirement_count: int) -> bool:
        sentence_count = sum(text.count(mark) for mark in "。；;\n") + 1
        competing_clauses = text.count("，") + text.count(",")
        return (
            len(text) >= 80
            or sentence_count >= 3
            or requirement_count >= 2
            or (len(text) >= 60 and competing_clauses >= 3)
        )
