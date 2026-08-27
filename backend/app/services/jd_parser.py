from datetime import date

from app.schemas.analysis import JDRequirements, JDRequirementsOutput, KeyRequirement
from app.services.claude_client import ClaudeStructuredClient


class JDParser:
    PROMPT_VERSION = "job-jd-v3"
    SCHEMA_VERSION = "jd-requirements-v3"

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
        return self._to_requirements(output)

    @staticmethod
    def _to_requirements(output: JDRequirementsOutput) -> JDRequirements:
        published_date: date | None = None
        if output.published_date.strip():
            try:
                published_date = date.fromisoformat(output.published_date.strip())
            except ValueError:
                published_date = None
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
            knowledge_topics=JDParser._items(output.knowledge_topics),
            responsibilities=JDParser._items(output.responsibilities),
            required_skills=JDParser._items(output.required_skills),
            preferred_skills=JDParser._items(output.preferred_skills),
            ai_requirements=JDParser._items(output.ai_requirements),
            product_requirements=JDParser._items(output.product_requirements),
            technical_requirements=JDParser._items(output.technical_requirements),
            domain_requirements=JDParser._items(output.domain_requirements),
        )

    @staticmethod
    def _optional(value: str) -> str | None:
        cleaned = " ".join(value.split())
        return cleaned or None

    @staticmethod
    def _items(values: list[str]) -> list[str]:
        return [cleaned for value in values if (cleaned := " ".join(value.split()))]
