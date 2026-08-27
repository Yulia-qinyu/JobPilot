from app.schemas.analysis import ResumeProfile
from app.services.claude_client import ClaudeStructuredClient


class ResumeParser:
    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def parse(self, resume_text: str) -> ResumeProfile:
        return self.client.generate(
            tool_name="submit_resume_profile",
            output_model=ResumeProfile,
            prompt=f"""You are a precise resume parser. Extract only facts supported by the resume.
Do not infer missing employers, dates, credentials, metrics, or skills. Keep useful context in
experience highlights. Use empty arrays or null fields when information is absent. Preserve factual
content in the resume's original language; do not translate company, project, or technology names.

RESUME:
{resume_text}
""",
        )
