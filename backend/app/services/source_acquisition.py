from collections.abc import Callable

from app.services.job_sources.base import JobSourceAdapter, SourceJobRecord, SourceSearchQuery

PageProgress = Callable[[int, int, int], None]


class SourceAcquisitionService:
    """Source-neutral acquisition. It never writes a Job."""

    def discover(
        self,
        adapter: JobSourceAdapter,
        query: SourceSearchQuery,
        *,
        on_page: PageProgress | None = None,
        max_records: int | None = None,
    ) -> tuple[list[SourceJobRecord], int]:
        records: list[SourceJobRecord] = []
        seen: set[tuple[str, str]] = set()
        duplicates = 0
        for page in adapter.discover(query):
            for record in page.records:
                if max_records is not None and len(records) >= max_records:
                    break
                identity = (record.source, record.external_job_id)
                if record.external_job_id and identity in seen:
                    duplicates += 1
                    continue
                if record.external_job_id:
                    seen.add(identity)
                records.append(record)
            if on_page:
                on_page(page.offset, len(page.records), page.total_count)
            if max_records is not None and len(records) >= max_records:
                break
        return records, duplicates
