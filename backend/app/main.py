import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.analysis import router as analysis_router
from app.routes.dashboard import router as dashboard_router
from app.routes.discovery import router as discovery_router
from app.routes.job_analysis import router as job_analysis_router
from app.routes.job_decisions import job_router as job_decision_job_router
from app.routes.job_decisions import router as job_decisions_router
from app.routes.job_imports import router as job_imports_router
from app.routes.jobs import router as jobs_router
from app.routes.profile import router as profile_router
from app.routes.resume_tailoring import router as resume_tailoring_router
from app.routes.workspace import router as workspace_router

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)
app_logger.disabled = False
app_logger.handlers.clear()
app_logger.propagate = True
# Uvicorn configures logging before importing this module and can disable loggers
# that were created while route modules were imported. Re-enable only JobPilot's
# own logger namespace so stage/timing metrics remain visible.
for logger_name in logging.root.manager.loggerDict:
    if logger_name.startswith("app."):
        logging.getLogger(logger_name).disabled = False
app = FastAPI(title="JobPilot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.include_router(analysis_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(job_analysis_router)
app.include_router(job_imports_router)
app.include_router(job_decisions_router)
app.include_router(job_decision_job_router)
app.include_router(resume_tailoring_router)
app.include_router(dashboard_router)
app.include_router(discovery_router)
app.include_router(workspace_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
