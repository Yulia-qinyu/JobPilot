import json

from app.schemas.fit_analysis import FitAnalysisOutput
from app.services.claude_client import ClaudeStructuredClient
from app.services.evidence_catalog import EvidenceCatalog, EvidenceCatalogBuilder
from app.services.requirement_catalog import RequirementCatalog


class RequirementMatcher:
    PROMPT_VERSION = "job-fit-v2-candidate-identity"
    SCHEMA_VERSION = "fit-analysis-wire-v1"

    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def analyze(
        self,
        requirements: RequirementCatalog,
        evidence: EvidenceCatalog,
    ) -> FitAnalysisOutput:
        requirement_payload = [
            {
                "requirement_id": item.requirement_id,
                "requirement_text": item.text,
                "context": item.context,
                "importance_hint": item.importance_hint,
                "source_kind": item.source_kind,
            }
            for item in requirements.requirements
        ]
        evidence_payload = [
            {
                "evidence_source_id": EvidenceCatalogBuilder.catalog_id(item),
                "source_type": item.source_type,
                "text": item.text,
                "context": item.context,
            }
            for item in evidence.sources
        ]
        return self.client.generate(
            tool_name="submit_requirement_matches",
            output_model=FitAnalysisOutput,
            prompt=f"""You are JobPilot's evidence-grounded requirement matcher. Match every supplied
job requirement against only the supplied candidate evidence catalog. Return exactly one
requirement_match for every requirement_id, with no duplicates and no unknown IDs.

MATCH RULES:
- Strong: direct, convincing evidence satisfies the requirement.
- Partial: related evidence exists but scope, depth, duration, or exact capability is incomplete.
- Missing: no eligible evidence supports the requirement. Missing must use an empty evidence list.
- Strong and Partial must cite one or more exact evidence_source_ids from the catalog.
- Cite at most the four strongest, most direct evidence sources for each requirement.
- Never invent candidate facts, achievements, dates, employers, credentials, or evidence IDs.
- A resume skill keyword alone is normally Partial unless other factual evidence demonstrates use.
- Evidence IDs beginning with manual_confirmed:profile: are user-confirmed Candidate Profile facts.
- A confirmed graduation cohort supports only that cohort/campus identity; it does not prove a degree.
- For a compound requirement such as "2027届本科及以上学历", use Strong only when separate
  eligible evidence supports both the graduation cohort and the required degree. Use Partial when
  only one component is supported. Never infer a degree from graduation cohort metadata.

IMPORTANCE:
- Critical: central explicit requirement or essential responsibility.
- Important: meaningful requirement that is not a strict gate.
- Preferred: preferred, plus, nice-to-have, familiar-with, 优先, 熟悉, or 加分 language.

HARD REQUIREMENTS — BE CONSERVATIVE:
- Mark hard only when the requirement itself contains explicit mandatory or eligibility language,
  such as must, required, mandatory, at least X years, a required certification/degree/license,
  legal work eligibility, an explicit graduating cohort/date, 必须, 至少, 不少于, 工作许可,
  明确毕业届别, or mandatory qualification language.
- Never mark preferred, familiar with, plus, nice to have, 优先, 熟悉, or 加分 as hard.
- A hard requirement must use importance Critical.
- hard_requirement_category must be eligibility, experience, qualification, other, or none.
- Use none whenever is_hard_requirement is false.

OUTPUT:
- Write summary, reasons, preparation titles, and actions in natural Simplified Chinese.
- Keep each reason focused and concise, normally no more than two sentences.
- Preserve company, project, and technology names such as AI, LLM, Agent, RAG, SQL, and Python.
- suggested_preparation must be concise, prioritized, linked to valid requirement IDs, and must not
  rewrite the resume or tell the user to claim unsupported experience.

JOB REQUIREMENTS:
{json.dumps(requirement_payload, ensure_ascii=False)}

ELIGIBLE CANDIDATE EVIDENCE:
{json.dumps(evidence_payload, ensure_ascii=False)}
""",
        )
