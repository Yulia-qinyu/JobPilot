import json

from app.schemas.analysis import JDRequirements, MatchAnalysis, ResumeProfile
from app.services.claude_client import ClaudeStructuredClient


class Matcher:
    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def analyze(
        self,
        target_position: str,
        profile: ResumeProfile,
        requirements: JDRequirements,
    ) -> MatchAnalysis:
        return self.client.generate(
            tool_name="submit_match_analysis",
            output_model=MatchAnalysis,
            prompt=f"""Act as a pragmatic hiring-side evaluator for {target_position}. Compare only the
structured resume evidence and job requirements below. Be specific and evidence-based; never invent
candidate experience. Score 0-100. Use these recommendation bands consistently:
- Strong Apply: 80-100 and no critical required-skill gap
- Apply: 65-79
- Stretch: 45-64
- Skip: 0-44
If a critical required skill is missing, do not recommend Strong Apply. Preparation suggestions must
be concrete actions for an interview or application, not claims the candidate should add without proof.

LANGUAGE AND PRESENTATION RULES:
- Write every user-facing string in Simplified Chinese: strengths, gaps, evidence requirement summaries,
  resume evidence explanations, and preparation recommendations.
- Keep the recommendation field as exactly one of the English enum values required by the schema:
  Strong Apply, Apply, Stretch, or Skip. The UI localizes that enum.
- Do not translate factual company names, project names, product names, or technology names.
- Preserve natural English technical terms such as AI, LLM, Agent, RAG, SQL, Python, and Product Manager
  when that is clearer than a forced translation.
- Make key gaps distinct. Merge obviously duplicated or highly overlapping gaps into one concise gap.
- Rank preparation recommendations by priority, with the highest-impact actions first.

RESUME PROFILE:
{json.dumps(profile.model_dump(), ensure_ascii=False)}

JOB REQUIREMENTS:
{json.dumps(requirements.model_dump(), ensure_ascii=False)}
""",
        )
