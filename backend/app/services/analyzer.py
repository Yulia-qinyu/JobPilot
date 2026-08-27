import logging
from time import perf_counter

from app.schemas.analysis import AnalysisResponse
from app.services.jd_parser import JDParser
from app.services.matcher import Matcher
from app.services.resume_parser import ResumeParser

logger = logging.getLogger(__name__)


class JobAnalyzer:
    def __init__(self, resume_parser: ResumeParser, jd_parser: JDParser, matcher: Matcher):
        self.resume_parser = resume_parser
        self.jd_parser = jd_parser
        self.matcher = matcher

    def analyze(self, resume_text: str, target_position: str, jd_text: str) -> AnalysisResponse:
        analysis_started_at = perf_counter()
        stage_started_at = perf_counter()
        profile = self.resume_parser.parse(resume_text)
        logger.info(
            "Analysis stage completed stage=resume_parser elapsed_seconds=%.3f status=success",
            perf_counter() - stage_started_at,
        )

        stage_started_at = perf_counter()
        requirements = self.jd_parser.parse(target_position, jd_text)
        logger.info(
            "Analysis stage completed stage=jd_parser elapsed_seconds=%.3f status=success",
            perf_counter() - stage_started_at,
        )

        stage_started_at = perf_counter()
        match = self.matcher.analyze(target_position, profile, requirements)
        logger.info(
            "Analysis stage completed stage=match_analyzer elapsed_seconds=%.3f status=success",
            perf_counter() - stage_started_at,
        )

        stage_started_at = perf_counter()
        response = AnalysisResponse(
            resume_profile=profile,
            jd_requirements=requirements,
            match_analysis=match,
        )
        logger.info(
            "Analysis stage completed stage=response_assembly elapsed_seconds=%.3f status=success",
            perf_counter() - stage_started_at,
        )
        logger.info(
            "Analysis pipeline completed elapsed_seconds=%.3f claude_api_calls=3 "
            "claude_calls_sequential=true status=success",
            perf_counter() - analysis_started_at,
        )
        return response
