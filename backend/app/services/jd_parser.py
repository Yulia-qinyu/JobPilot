import unicodedata
from datetime import date

from app.schemas.analysis import (
    JDRequirements,
    JDRequirementsOutput,
    KeyRequirement,
    StructuredRequirement,
)
from app.services.claude_client import ClaudeStructuredClient
from app.services.requirement_catalog import RequirementCatalogBuilder


class JDParser:
    PROMPT_VERSION = "job-jd-v4-requirement-taxonomy"
    SCHEMA_VERSION = "jd-requirements-v4"
    MAX_REQUIREMENTS = 40

    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def parse(self, target_position: str | None, jd_text: str) -> JDRequirements:
        target_context = target_position.strip() if target_position else "Not provided"
        output = self.client.generate(
            tool_name="submit_jd_requirements",
            output_model=JDRequirementsOutput,
            prompt=f"""You are a precise job-description parser. Structure only information supported
by the supplied job description. Never invent a company, location, date, responsibility, skill, or
requirement. Use an empty string or an empty list when the source does not establish a value.
Distinguish required skills from preferred skills and preserve concrete scope, seniority, domain,
product, AI, and technical expectations.

Create a concise JD Quick Overview as part of the structured result:
- role_summary: one or two Simplified Chinese sentences describing the role's fundamental purpose.
- key_requirements: the 3-7 most important JD-backed requirements in priority order. Write each title
  and explanation in concise Simplified Chinese and classify priority as high, medium, or low.
- knowledge_topics: concise JD-derived knowledge, technologies, product concepts, or capabilities.
  Preserve natural terms such as LLM, Agent, RAG, SQL, Python, and A/B Testing.

Also extract canonical requirement suggestions. Each must quote source_text that appears verbatim in
the supplied JD and provide one independently judgeable normalized_requirement. Split a compound
sentence only when it explicitly states independent requirements. Never turn theoretical knowledge
into an invented practical-experience requirement.

Classify by EVIDENCE VERIFIABILITY, not by a single keyword:
- eligibility: explicit degree, graduation cohort, minimum duration, certification, work
  authorization, or mandatory language qualification. A duration such as "3年以上 AI 产品经验"
  is eligibility only; do not duplicate it as a matchable AI-product requirement.
- matchable: career evidence can reasonably verify experience or practical capability, such as SQL
  use, RAG implementation, product delivery, data analysis, or industry experience.
- knowledge: theoretical understanding, principles, mechanisms, architecture, or capability
  boundaries that resume-style evidence cannot consistently prove.
- subjective: attitude statements such as passion, enthusiasm, or learning willingness. These are
  retained for display only and are never scored.

Use eligibility_category=none for non-eligibility requirements. Eligibility must use Critical.
Use Preferred only for an explicit bonus/preference. "熟练使用 SQL" is matchable; "理解 RAG 原理和
能力边界" is knowledge; "有金融行业经验优先" is Preferred matchable. For knowledge requirements,
return concise knowledge_topics. The separate knowledge_topics overview will be ignored by V2 and
derived by the backend from these canonical knowledge requirements.

The quick overview is only a summary of the job. Do not compare against a resume, infer candidate gaps,
or give personalized advice. Keep extracted responsibilities and qualification text in the JD's source
language. Do not translate factual company, project, product, or technology names. Only return an exact
published date when the source provides one; otherwise use an empty string. Format an established
date as YYYY-MM-DD.

USER'S TARGET POSITION (optional hint): {target_context}

JOB DESCRIPTION:
{jd_text}
""",
        )
        return self._to_requirements(output, jd_text)

    @classmethod
    def _to_requirements(
        cls, output: JDRequirementsOutput, jd_text: str
    ) -> JDRequirements:
        published_date: date | None = None
        if output.published_date.strip():
            try:
                published_date = date.fromisoformat(output.published_date.strip())
            except ValueError:
                published_date = None
        canonical, subjective = cls._canonical_requirements(output, jd_text)
        knowledge_topics = cls._deduplicate(
            topic
            for item in canonical
            if item.requirement_type == "knowledge"
            for topic in item.knowledge_topics
        )
        return JDRequirements(
            role=JDParser._optional(output.role),
            company=JDParser._optional(output.company),
            location=JDParser._optional(output.location),
            recruitment_type=JDParser._optional(output.recruitment_type),
            published_date=published_date,
            role_summary=JDParser._optional(output.role_summary),
            key_requirements=[
                KeyRequirement(
                    title=item.title.strip(),
                    explanation=item.explanation.strip(),
                    category=JDParser._optional(item.category),
                    priority=item.priority,
                )
                for item in output.key_requirements
                if item.title.strip() and item.explanation.strip()
            ],
            knowledge_topics=knowledge_topics,
            responsibilities=JDParser._items(output.responsibilities),
            required_skills=JDParser._items(output.required_skills),
            preferred_skills=JDParser._items(output.preferred_skills),
            ai_requirements=JDParser._items(output.ai_requirements),
            product_requirements=JDParser._items(output.product_requirements),
            technical_requirements=JDParser._items(output.technical_requirements),
            domain_requirements=JDParser._items(output.domain_requirements),
            requirement_taxonomy_version="v2",
            requirements=canonical,
            subjective_expectations=subjective,
        )

    @classmethod
    def _canonical_requirements(
        cls, output: JDRequirementsOutput, jd_text: str
    ) -> tuple[list[StructuredRequirement], list[str]]:
        normalized_jd = cls._trace_text(jd_text)
        admitted: list[tuple[object, str, str]] = []
        subjective: list[str] = []
        seen: set[tuple[str, str, str, str]] = set()
        for item in output.requirements[: cls.MAX_REQUIREMENTS]:
            source_text = " ".join(item.source_text.split())[:1000]
            normalized_requirement = " ".join(item.normalized_requirement.split())[:500]
            source_key = cls._trace_text(source_text)
            if (
                not source_text
                or not normalized_requirement
                or not source_key
                or source_key not in normalized_jd
            ):
                continue
            if item.requirement_type == "subjective":
                subjective.append(source_text)
                continue
            key = (
                source_key,
                cls._trace_text(normalized_requirement),
                item.requirement_type,
                item.source_section,
            )
            if key in seen:
                continue
            seen.add(key)
            admitted.append((item, source_text, normalized_requirement))

        duration_sources = {
            cls._trace_text(source_text)
            for item, source_text, _ in admitted
            if item.requirement_type == "eligibility"
            and item.eligibility_category == "experience_years"
        }
        canonical: list[StructuredRequirement] = []
        for item, source_text, normalized_requirement in admitted:
            if (
                item.requirement_type == "matchable"
                and cls._trace_text(source_text) in duration_sources
            ):
                # Avoid double counting the same duration statement. An independently
                # expressed practical requirement should use its own source clause.
                continue
            eligibility_category = (
                item.eligibility_category
                if item.requirement_type == "eligibility"
                and item.eligibility_category != "none"
                else None
            )
            importance = "Critical" if item.requirement_type == "eligibility" else item.importance
            topics = (
                cls._deduplicate(cls._items(item.knowledge_topics))[:8]
                if item.requirement_type == "knowledge"
                else []
            )
            requirement_id = RequirementCatalogBuilder.stable_requirement_id(
                source_text=source_text,
                normalized_requirement=normalized_requirement,
                requirement_type=item.requirement_type,
                source_section=item.source_section,
            )
            canonical.append(
                StructuredRequirement(
                    requirement_id=requirement_id,
                    source_text=source_text,
                    normalized_requirement=normalized_requirement,
                    source_section=item.source_section,
                    requirement_type=item.requirement_type,
                    importance=importance,
                    eligibility_category=eligibility_category,
                    knowledge_topics=topics,
                )
            )
        return canonical, cls._deduplicate(subjective)

    @staticmethod
    def _optional(value: str) -> str | None:
        cleaned = " ".join(value.split())
        return cleaned or None

    @staticmethod
    def _items(values: list[str]) -> list[str]:
        return [cleaned for value in values if (cleaned := " ".join(value.split()))]

    @staticmethod
    def _trace_text(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    @staticmethod
    def _deduplicate(values) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = " ".join(value.split())
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result
