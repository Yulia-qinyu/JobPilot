from app.db.models import JobAnalysis
from app.services.requirement_matcher import RequirementMatcher


def analysis_identity_is_current(
    analysis: JobAnalysis,
    *,
    resume_hash: str,
    experience_bank_hash: str,
    structured_jd_hash: str,
    matcher_model: str,
    enforce_matcher_version: bool = True,
) -> bool:
    """Single compatibility boundary for consumers of a persisted fit analysis."""

    return (
        analysis.resume_hash == resume_hash
        and analysis.experience_bank_hash == experience_bank_hash
        and analysis.structured_jd_hash == structured_jd_hash
        and (
            not enforce_matcher_version
            or (
                analysis.matcher_model == matcher_model
                and analysis.matcher_prompt_version == RequirementMatcher.PROMPT_VERSION
                and analysis.matcher_schema_version == RequirementMatcher.SCHEMA_VERSION
            )
        )
    )
