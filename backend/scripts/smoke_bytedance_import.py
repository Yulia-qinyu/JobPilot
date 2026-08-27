"""Run an explicit, sanitized live ByteDance import smoke test.

This script is intentionally excluded from automated tests. It prints only IDs,
counts, elapsed time, and terminal status; no job body or upstream response data.
"""

import argparse
import json
from time import perf_counter

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.job_import_service import JobImportService
from app.services.job_sources.bytedance import ByteDanceJobSource
from app.services.job_sources.registry import JobSourceRegistry


class CountingByteDanceJobSource(ByteDanceJobSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages_requested = 0

    def discover(self, query):
        for page in super().discover(query):
            self.pages_requested += 1
            yield page


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("search_url")
    args = parser.parse_args()
    settings = get_settings()
    adapter = CountingByteDanceJobSource(settings)
    registry = JobSourceRegistry([adapter])
    started = perf_counter()
    try:
        with SessionLocal() as db:
            service = JobImportService(db, settings, registry)
            session_id = service.create_session(args.search_url).id
            service.run(session_id)
            result = service.get_session(session_id)
            print(
                json.dumps(
                    {
                        "session_id": session_id,
                        "status": result.status,
                        "pages_requested": adapter.pages_requested,
                        "discovered": result.discovered_count,
                        "processed": result.processed_count,
                        "imported": result.imported_count,
                        "updated": result.updated_count,
                        "duplicates": result.duplicate_count,
                        "failed": result.failed_count,
                        "result_jobs": len(result.result_job_ids),
                        "duration_seconds": round(perf_counter() - started, 3),
                        "claude_api_calls": 0,
                    },
                    ensure_ascii=False,
                )
            )
    finally:
        registry.close()


if __name__ == "__main__":
    main()
