import json

from app.schemas.fit_analysis import FitAnalysisOutput
from app.services.evidence_catalog import EvidenceCatalog, EvidenceCatalogBuilder
from app.services.matcher_client import (
    IMPORTANCE_FROM_HINT,
    StructuredMatcherClient,
)
from app.services.requirement_catalog import RequirementCatalog

# Frozen instruction block: job-fit-v3-rubric-refined-v2.
# Source of truth (byte-identical):
#   backend/evals/prompt_refinement_round2b/prompt_refinement_treatment_instructions.txt
# This is the exact treatment prompt used in the frozen T5 held-out finalist
# evaluation. Do not edit it here; change the frozen artifact and this copy
# together (tests assert they match).
PROMPT_C_INSTRUCTIONS = """You are JobPilot's evidence-grounded requirement matcher. Match every supplied
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

ADJUDICATION RULES (rubric-refined v2 — three calibration clarifications only; no new taxonomy,
scoring, eligibility, knowledge, OR-list, compound-decomposition, company, title, or preference
logic; no examples):

A. TECHNOLOGY ADJACENCY
- Related or adjacent technology is not automatically Partial. A Partial match requires evidence
  that meaningfully overlaps with the actual capability being requested.
- General AI / LLM / RAG experience alone should not automatically count as experience with a
  distinct specialised capability such as multimodal systems, speech / ASR, reinforcement-learning
  training, fine-tuning, model-training infrastructure, or specialised recommendation / search
  mechanisms.
- If the evidence is only general or neighbouring and does not demonstrate the requested
  capability, classify Missing.

B. PROJECT EXPERIENCE VS FORMAL WORK EXPERIENCE
- Project experience is valid matchable evidence. A direct and complete project may support Strong
  when the requirement asks for related practical experience, implementation, delivery,
  productisation, or hands-on application.
- When the requirement explicitly asks for formal professional-role experience, years in a job
  function, seniority, industry tenure, or professional ownership scope, project experience alone
  should not be treated as equivalent formal work experience. Relevant project evidence may support
  Partial in those cases.

C. STRONG / PARTIAL / MISSING CALIBRATION
- Strong: direct and sufficiently complete evidence at the level actually requested.
- Partial: meaningful but materially incomplete evidence.
- Missing: no meaningful evidence for the requested capability, or only general / adjacent evidence
  that does not demonstrate it.
- Do not use Partial merely because the model is uncertain.

IMPORTANCE:
- Critical: central explicit requirement or essential responsibility.
- Important: meaningful requirement that is not a strict gate.
- Preferred: only an explicit preferred, plus, nice-to-have, 优先, or 加分 requirement. Words
  such as 熟悉/familiar describe proficiency and do not alone make a requirement Preferred.

HARD REQUIREMENTS — BE CONSERVATIVE:
- Mark hard only when the requirement itself contains explicit mandatory or eligibility language,
  such as must, required, mandatory, at least X years, a required certification/degree/license,
  legal work eligibility, an explicit graduating cohort/date, 必须, 至少, 不少于, 工作许可,
  明确毕业届别, or mandatory qualification language.
- Never mark preferred, familiar with, plus, nice to have, 优先, 熟悉, or 加分 as hard.
- A hard requirement must use importance Critical.
- hard_requirement_category must be eligibility, experience, qualification, other, or none.
- Use none whenever is_hard_requirement is false.
- Requirements with source_kind=v2_matchable have already passed the V2 taxonomy boundary. They
  are evidence-matchable capabilities, never eligibility gates; return is_hard_requirement=false
  and hard_requirement_category=none for them.

OUTPUT:
- Write summary, reasons, preparation titles, and actions in natural Simplified Chinese.
- Keep each reason focused and concise, normally no more than two sentences.
- Preserve company, project, and technology names such as AI, LLM, Agent, RAG, SQL, and Python.
- suggested_preparation must be concise, prioritized, linked to valid requirement IDs, and must not
  rewrite the resume or tell the user to claim unsupported experience."""


class RequirementMatcher:
    PROMPT_VERSION = "job-fit-v3-rubric-refined-v2"
    SCHEMA_VERSION = "fit-analysis-wire-v2"

    def __init__(self, client: StructuredMatcherClient):
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
        importance_by_requirement_id = {
            item.requirement_id: IMPORTANCE_FROM_HINT.get(
                item.importance_hint, "Important"
            )
            for item in requirements.requirements
        }
        prompt = (
            f"{PROMPT_C_INSTRUCTIONS}\n\n"
            f"JOB REQUIREMENTS:\n"
            f"{json.dumps(requirement_payload, ensure_ascii=False)}\n\n"
            f"ELIGIBLE CANDIDATE EVIDENCE:\n"
            f"{json.dumps(evidence_payload, ensure_ascii=False)}\n"
        )
        return self.client.generate_fit_analysis(
            prompt=prompt,
            importance_by_requirement_id=importance_by_requirement_id,
            tool_name="submit_requirement_matches",
        )
