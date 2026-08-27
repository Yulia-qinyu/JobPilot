from app.schemas.discovery import (
    CandidateConstraintSignal,
    CandidateEvidenceTrace,
    CandidatePersonalizationReason,
    DiscoveryPersonalizationDerived,
    DiscoveryResult,
)
from app.schemas.discovery_personalization import PersonalizedRankingInput
from app.services.candidate_discovery_context import TOPIC_PATTERNS

ROLE_TOPICS = {
    "ai_product": {"ai_product"},
    "fintech_product": {"fintech"},
    "data_product": {"data"},
    "growth_product": {"growth"},
    "platform_product": {"platform"},
}
TOPIC_LABELS = {
    "ai_product": "AI 产品",
    "agent": "Agent",
    "llm": "大模型",
    "fintech": "FinTech",
    "data": "数据",
    "growth": "增长",
    "platform": "平台",
    "enterprise_tob": "ToB",
    "experimentation": "实验 / 评测",
    "product_ownership": "产品职责",
    "ecommerce": "电商",
    "international": "国际化",
    "content_creator": "内容 / 创作者",
    "ads_commercialization": "广告 / 商业化",
}
DEGREE_VALUES = {"associate": 1, "bachelor": 2, "master": 3, "doctor": 4}


class DiscoveryPersonalizationService:
    VERSION = "discovery-personalization-v1"

    def apply(
        self, result: DiscoveryResult, ranking_input: PersonalizedRankingInput
    ) -> DiscoveryResult:
        candidate = ranking_input.candidate_context
        evidence_by_ref = candidate.evidence_by_ref
        job_topics = self._job_topics(result)
        candidate_topics = {item.topic: item.evidence_refs for item in candidate.evidence_topics}
        matching_topics = sorted(job_topics & candidate_topics.keys())
        reasons: list[CandidatePersonalizationReason] = []
        used_refs: list[str] = []
        for topic in matching_topics[:4]:
            refs = list(candidate_topics[topic][:3])
            used_refs.extend(refs)
            reasons.append(
                CandidatePersonalizationReason(
                    reason_type="candidate_evidence_match",
                    display=f"存在可支持的{TOPIC_LABELS.get(topic, topic)}相关经历",
                    evidence_refs=refs,
                )
            )

        requested = set(ranking_input.search_context.explicit_constraints.role_families)
        requested_functions = set(
            ranking_input.search_context.explicit_constraints.job_functions
        )
        role_alignment = next(
            (
                role
                for role in ranking_input.saved_preferences.target_roles
                if role.role_family == result.deterministic_derived.role_family
                and role.role_family != "unknown"
                and (
                    not requested_functions
                    or "product_management" in requested_functions
                )
                and (not requested or role.role_family in requested)
            ),
            None,
        )
        if role_alignment is not None:
            reasons.append(
                CandidatePersonalizationReason(
                    reason_type="target_role_alignment",
                    display="对应我已设置的目标岗位方向",
                    evidence_refs=[role_alignment.evidence_ref],
                )
            )
            used_refs.append(role_alignment.evidence_ref)

        constraints = [
            self._constraint(signal, ranking_input)
            for signal in result.deterministic_derived.explicit_hard_signals
            if signal.type in {"experience_years", "degree"}
        ]
        has_gap = any(item.status == "PotentialGap" for item in constraints)
        public_band = result.search_derived.relevance_band
        if public_band == "Low":
            band = "Neutral"
        elif matching_topics and public_band == "High" and not has_gap:
            band = "Strong"
        else:
            band = "Relevant"

        traces = []
        for ref in dict.fromkeys(used_refs):
            evidence = evidence_by_ref.get(ref)
            if evidence is not None:
                traces.append(
                    CandidateEvidenceTrace(
                        evidence_ref=ref,
                        source_type=evidence.source_type,  # type: ignore[arg-type]
                        text_summary=" ".join(evidence.text.split())[:240],
                        context=evidence.context,
                    )
                )
                continue
            target = next(
                (
                    role
                    for role in ranking_input.saved_preferences.target_roles
                    if role.evidence_ref == ref
                ),
                None,
            )
            if target is not None:
                traces.append(
                    CandidateEvidenceTrace(
                        evidence_ref=ref,
                        source_type="target_role",
                        text_summary=f"{target.name} · {target.priority}",
                        context="已保存的目标岗位",
                    )
                )
        return result.model_copy(
            update={
                "personalization_derived": DiscoveryPersonalizationDerived(
                    band=band,
                    candidate_reasons=reasons,
                    candidate_constraint_signals=constraints,
                    evidence=traces,
                )
            }
        )

    @staticmethod
    def remove(result: DiscoveryResult) -> DiscoveryResult:
        return result.model_copy(update={"personalization_derived": None})

    @staticmethod
    def _job_topics(result: DiscoveryResult) -> set[str]:
        topics = set(ROLE_TOPICS.get(result.deterministic_derived.role_family, set()))
        searchable = f"{result.normalized.role} {result.normalized.original_jd}"
        topics.update(
            topic for topic, pattern in TOPIC_PATTERNS.items() if pattern.search(searchable)
        )
        return topics

    @staticmethod
    def _constraint(signal, ranking_input: PersonalizedRankingInput) -> CandidateConstraintSignal:
        candidate = ranking_input.candidate_context
        if signal.type == "experience_years":
            refs = [
                item.evidence_ref for item in candidate.evidence if item.context == "工作经历"
            ]
            if candidate.professional_years is None:
                return CandidateConstraintSignal(
                    type="experience_years",
                    status="Unknown",
                    display="当前档案无法确认该经验年限门槛",
                )
            required = float(signal.value or 0)
            status = "Supported" if candidate.professional_years >= required else "PotentialGap"
            display = (
                "当前已验证经历年限支持该要求"
                if status == "Supported"
                else f"可能存在 {int(required)}+ 年经验门槛差距"
            )
            return CandidateConstraintSignal(
                type="experience_years", status=status, display=display, evidence_refs=refs
            )
        refs = [item.evidence_ref for item in candidate.evidence if item.context == "教育经历"]
        if candidate.education_level is None:
            return CandidateConstraintSignal(
                type="degree", status="Unknown", display="当前档案无法确认该学历门槛"
            )
        required_level = DEGREE_VALUES.get(str(signal.value), 0)
        status = "Supported" if candidate.education_level >= required_level else "PotentialGap"
        return CandidateConstraintSignal(
            type="degree",
            status=status,
            display=(
                "当前已验证学历支持该要求"
                if status == "Supported"
                else "可能存在明确学历门槛差距"
            ),
            evidence_refs=refs,
        )
