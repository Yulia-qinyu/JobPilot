import re
from collections import defaultdict
from typing import Protocol

from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import ResumeProfile
from app.schemas.discovery_personalization import (
    CandidateDiscoveryContext,
    CandidateEvidenceItem,
    CandidateEvidenceTopic,
    PersonalizedRankingInput,
    SavedCareerPreferences,
    SavedTargetRole,
)
from app.services.eligibility_service import EligibilityService
from app.services.evidence_catalog import EvidenceCatalogBuilder, canonical_hash

TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "ai_product": re.compile(r"AI.{0,18}产品|产品.{0,18}AI|人工智能产品", re.IGNORECASE),
    "agent": re.compile(r"\bagent(?:ic)?\b|智能体", re.IGNORECASE),
    "llm": re.compile(r"\bLLMs?\b|large language model|大模型", re.IGNORECASE),
    "fintech": re.compile(r"fintech|金融科技|支付|信贷|银行|financial", re.IGNORECASE),
    "data": re.compile(r"数据|analytics?|分析|SQL|BI\b", re.IGNORECASE),
    "growth": re.compile(r"增长|growth|conversion|转化", re.IGNORECASE),
    "platform": re.compile(r"平台|platform|infrastructure", re.IGNORECASE),
    "enterprise_tob": re.compile(r"\bB2B\b|\bToB\b|企业服务|enterprise", re.IGNORECASE),
    "experimentation": re.compile(r"A/B|experiment|实验|评测|evaluation", re.IGNORECASE),
    "product_ownership": re.compile(
        r"product owner|产品负责人|产品经理|主导|owned|led", re.IGNORECASE
    ),
    "ecommerce": re.compile(r"电商|e-?commerce|merchant|商户", re.IGNORECASE),
    "international": re.compile(r"出海|国际化|global|international", re.IGNORECASE),
    "content_creator": re.compile(r"内容|创作者|creator|短剧", re.IGNORECASE),
    "ads_commercialization": re.compile(r"广告|商业化|ads?\b", re.IGNORECASE),
}
AI_TOPIC = re.compile(r"\bAI\b|人工智能|大模型|\bLLM\b|\bAgent\b|智能体", re.IGNORECASE)
PRODUCT_TOPIC = re.compile(r"产品|product\s*(?:manager|owner|lead)|\bPM\b", re.IGNORECASE)

DEGREE_LEVELS = {
    "associate": 1,
    "大专": 1,
    "专科": 1,
    "bachelor": 2,
    "本科": 2,
    "master": 3,
    "硕士": 3,
    "phd": 4,
    "doctor": 4,
    "博士": 4,
}


class CandidateDiscoveryContextProviderProtocol(Protocol):
    def load(self, search_context) -> PersonalizedRankingInput: ...


class CandidateDiscoveryContextError(RuntimeError):
    pass


class CandidateDiscoveryContextProvider:
    """Build one compact, verified, read-only context for a discovery session."""

    VERSION = "candidate-discovery-context-v1"

    def __init__(self, repository: ProfileRepository):
        self.repository = repository
        self.evidence_builder = EvidenceCatalogBuilder()

    def load(self, search_context) -> PersonalizedRankingInput:
        profile = self.repository.find_full_profile()
        if profile is None:
            return PersonalizedRankingInput(
                search_context=search_context,
                candidate_context=CandidateDiscoveryContext(
                    professional_years=None,
                    education_level=None,
                    graduation_year=None,
                    evidence=(),
                    evidence_topics=(),
                    context_version=canonical_hash({"version": self.VERSION, "profile": None}),
                    limited=True,
                ),
                saved_preferences=SavedCareerPreferences(
                    target_roles=(), preferred_location=None, target_companies=()
                ),
            )
        evidence_items: list[CandidateEvidenceItem] = []
        structured: ResumeProfile | None = None
        if profile.resume is not None:
            structured = ResumeProfile.model_validate(profile.resume.structured_profile)
            catalog = self.evidence_builder.build(profile)
            evidence_items = [
                CandidateEvidenceItem(
                    evidence_ref=self.evidence_builder.catalog_id(item),
                    source_type=item.source_type,
                    text=item.text,
                    context=item.context,
                )
                for item in catalog.sources
            ]

        topics: dict[str, list[str]] = defaultdict(list)
        for item in evidence_items:
            searchable = f"{item.text} {item.context}"
            for topic, pattern in TOPIC_PATTERNS.items():
                if pattern.search(searchable):
                    topics[topic].append(item.evidence_ref)
            if AI_TOPIC.search(searchable) and PRODUCT_TOPIC.search(searchable):
                topics["ai_product"].append(item.evidence_ref)

        candidate = CandidateDiscoveryContext(
            professional_years=(
                EligibilityService._professional_years(structured) if structured else None
            ),
            education_level=self._education_level(structured),
            graduation_year=(
                EligibilityService._graduation_year(structured) if structured else None
            ),
            evidence=tuple(evidence_items),
            evidence_topics=tuple(
                CandidateEvidenceTopic(topic=topic, evidence_refs=tuple(dict.fromkeys(refs)))
                for topic, refs in sorted(topics.items())
            ),
            context_version=canonical_hash(
                {
                    "version": self.VERSION,
                    "evidence": [
                        (item.evidence_ref, item.source_type, item.text, item.context)
                        for item in evidence_items
                    ],
                }
            ),
            limited=structured is None or not evidence_items,
        )
        preferences = SavedCareerPreferences(
            target_roles=tuple(
                SavedTargetRole(
                    evidence_ref=f"target_role:{item.id}",
                    name=item.name,
                    priority=item.priority,
                    role_family=item.effective_role_family,  # type: ignore[arg-type]
                )
                for item in profile.target_roles
            ),
            preferred_location=profile.preferred_location,
            target_companies=tuple(item.name for item in profile.target_companies),
        )
        return PersonalizedRankingInput(
            search_context=search_context,
            candidate_context=candidate,
            saved_preferences=preferences,
        )

    @staticmethod
    def _education_level(profile: ResumeProfile | None) -> int | None:
        if profile is None:
            return None
        levels = [
            level
            for education in profile.education
            for marker, level in DEGREE_LEVELS.items()
            if marker in f"{education.degree or ''} {education.field or ''}".casefold()
        ]
        return max(levels) if levels else None
