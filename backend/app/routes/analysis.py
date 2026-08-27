import logging
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import get_settings
from app.schemas.analysis import AnalysisResponse
from app.services.analyzer import JobAnalyzer
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient
from app.services.file_extractor import FileExtractionError, extract_resume_text
from app.services.jd_parser import JDParser
from app.services.matcher import Matcher
from app.services.resume_parser import ResumeParser

router = APIRouter(prefix="/api", tags=["V0.1 analysis"])
logger = logging.getLogger(__name__)


@lru_cache
def get_analyzer() -> JobAnalyzer:
    client = ClaudeStructuredClient(get_settings())
    return JobAnalyzer(ResumeParser(client), JDParser(client), Matcher(client))


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_job(
    resume: UploadFile = File(...),
    target_position: str = Form(..., min_length=2, max_length=200),
    job_description: str = Form(..., min_length=50, max_length=50_000),
    analyzer: JobAnalyzer = Depends(get_analyzer),
) -> AnalysisResponse:
    request_started_at = perf_counter()
    request_status = "error"
    settings = get_settings()
    filename = resume.filename or ""
    if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX resumes are supported.")

    stage_started_at = perf_counter()
    content = resume.file.read(settings.max_upload_bytes + 1)
    logger.info(
        "Analysis stage completed stage=resume_file_read elapsed_seconds=%.3f status=success",
        perf_counter() - stage_started_at,
    )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Resume must be 10 MB or smaller.")

    try:
        stage_started_at = perf_counter()
        resume_text = extract_resume_text(filename, content)
        logger.info(
            "Analysis stage completed stage=resume_text_extraction elapsed_seconds=%.3f "
            "status=success",
            perf_counter() - stage_started_at,
        )
        result = analyzer.analyze(resume_text, target_position.strip(), job_description.strip())
        request_status = "success"
        return result
    except FileExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        logger.info(
            "Analysis request completed total_elapsed_seconds=%.3f status=%s",
            perf_counter() - request_started_at,
            request_status,
        )
