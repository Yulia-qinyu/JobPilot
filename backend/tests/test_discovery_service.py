from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Job, JobAnalysis, JobDecision
from app.schemas.analysis import JDRequirements, KeyRequirement
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore
from app.services.job_sources.base import (
    ImportedJobDraft,
    SourceJobPage,
    SourceJobRecord,
    SourceSearchQuery,
)
from app.services.job_sources.bytedance import JobSourceError
from app.services.job_sources.registry import JobSourceRegistry


def engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def record(
    external_id: str,
    role: str = "AI Product Manager",
    requirement: str = "具备产品经验",
    recruitment_type: str = "experienced",
):
    return SourceJobRecord(
        source="bytedance",
        external_job_id=external_id,
        external_job_code=f"A-{external_id}",
        title=role,
        locations=("北京",),
        recruitment_type=recruitment_type,
        detail_url=f"https://jobs.bytedance.com/experienced/position/{external_id}/detail",
        description="负责 AI 产品规划并推动跨团队交付。",
        requirements=requirement,
        published_date=date(2026, 8, 25),
        source_metadata={"job_category": {"name": "产品"}},
    )


class FakeByteDanceAdapter:
    source = "bytedance"

    def __init__(self, records: list[SourceJobRecord]):
        self.records = records

    def supports(self, value: str) -> bool:
        return value.startswith("https://jobs.bytedance.com/")

    def parse_search_url(self, value: str) -> SourceSearchQuery:
        return SourceSearchQuery(
            source="bytedance",
            normalized_url=value,
            channel="society",
            keyword="AI Product",
            location_codes=("CT_11",),
            recruitment_ids=("101",),
        )

    def discover(self, _query):
        midpoint = min(100, len(self.records))
        yield SourceJobPage(tuple(self.records[:midpoint]), len(self.records), 0)
        if len(self.records) > midpoint:
            yield SourceJobPage(tuple(self.records[midpoint:]), len(self.records), midpoint)

    def normalize(self, item: SourceJobRecord) -> ImportedJobDraft:
        original = f"职位描述\n{item.description}\n\n职位要求\n{item.requirements}"
        return ImportedJobDraft(
            source="bytedance",
            external_job_id=item.external_job_id,
            external_job_code=item.external_job_code,
            company="字节跳动",
            role=item.title,
            location="北京",
            recruitment_type=item.recruitment_type,
            source_url=item.detail_url,
            original_jd=original,
            structured_jd=JDRequirements(
                company="字节跳动",
                role=item.title,
                location="北京",
                responsibilities=[item.description],
                required_skills=[item.requirements],
                key_requirements=[KeyRequirement(title="要求", explanation=item.requirements)],
            ),
            published_date=item.published_date,
            source_metadata=item.source_metadata,
            source_content_hash=__import__("hashlib").sha256(original.encode()).hexdigest(),
        )


class FailingAdapter(FakeByteDanceAdapter):
    def discover(self, _query):
        raise JobSourceError("source timeout")
        yield  # pragma: no cover - preserve generator protocol


class UnexpectedFailingAdapter(FakeByteDanceAdapter):
    def discover(self, _query):
        raise RuntimeError("unexpected source response")
        yield  # pragma: no cover - preserve generator protocol


def service(db: Session, adapter: FakeByteDanceAdapter, store=None):
    return DiscoveryService(
        db,
        store or InMemoryDiscoverySessionStore(),
        JobSourceRegistry([adapter]),
    )


def test_search_400_jobs_is_ephemeral_then_explicit_add_persists_one() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    records = [record(str(index)) for index in range(400)]
    store = InMemoryDiscoverySessionStore(max_results=500)
    with Session(db_engine, expire_on_commit=False) as db:
        discovery = service(db, FakeByteDanceAdapter(records), store)
        before = db.scalar(select(func.count(Job.id))) or 0
        session = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(session.id)
        after_search = db.scalar(select(func.count(Job.id))) or 0
        state = discovery.get_session(session.id)
        page = discovery.result_page(
            session.id,
            page=1,
            page_size=25,
            location="北京",
            company="字节",
            role_family="ai_product",
            relevance="High",
            already_in_my_jobs=False,
            source="bytedance",
            sort="relevance",
        )
        assert state.state == "Completed"
        assert state.result_count == 400
        assert page.total == 400
        assert before == after_search == 0
        assert all("适合你" not in " ".join(item.search_derived.reasons) for item in page.items)

        added = discovery.add_to_my_jobs(session.id, page.items[0].result_id)
        assert added.outcome == "created"
        assert added.claude_api_calls == 0 and added.phase3_calls == 0
        assert db.scalar(select(func.count(Job.id))) == 1
        assert db.scalar(select(func.count(JobDecision.id))) == 1
        assert db.scalar(select(func.count(JobAnalysis.id))) == 0

        repeated = discovery.add_to_my_jobs(session.id, page.items[0].result_id)
        assert repeated.outcome == "existing"
        assert db.scalar(select(func.count(Job.id))) == 1
        refreshed = discovery.result_page(
            session.id,
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=True,
            source=None,
            sort="relevance",
        )
        assert refreshed.total == 1
        assert refreshed.items[0].persistent_job_id == added.persistent_job_id


def test_result_page_filters_canonical_recruitment_channel() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    records = [
        record("campus-1", recruitment_type="campus"),
        record("experienced-1", recruitment_type="experienced"),
    ]
    with Session(db_engine) as db:
        discovery = service(db, FakeByteDanceAdapter(records))
        session = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(session.id)
        campus = discovery.result_page(
            session.id,
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=None,
            source=None,
            sort="relevance",
            recruitment_type="campus",
        )
        experienced = discovery.result_page(
            session.id,
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=None,
            source=None,
            sort="relevance",
            recruitment_type="experienced",
        )
        assert campus.total == 1
        assert campus.items[0].normalized.recruitment_type == "campus"
        assert experienced.total == 1
        assert experienced.items[0].normalized.recruitment_type == "experienced"


def test_session_dedupe_cap_and_source_update_preserve_user_fields() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    records = [record(str(index)) for index in range(6)] + [record("1")]
    adapter = FakeByteDanceAdapter(records)
    store = InMemoryDiscoverySessionStore(max_results=5)
    with Session(db_engine, expire_on_commit=False) as db:
        discovery = service(db, adapter, store)
        session = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(session.id)
        state = discovery.get_session(session.id)
        assert state.state == "Partial"
        assert state.result_cap_reached is True
        assert state.result_count == 5
        assert state.duplicate_count == 1
        page = discovery.result_page(
            session.id,
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=None,
            source=None,
            sort="relevance",
        )
        first = discovery.add_to_my_jobs(session.id, page.items[0].result_id)
        job = db.get(Job, first.persistent_job_id)
        job.status = "Preparing"
        job.notes = "preserve"
        db.commit()

        adapter.records = [record(job.external_job_id, requirement="明确要求至少 5 年经验")]
        second = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(second.id)
        changed = discovery.result_page(
            second.id,
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=True,
            source=None,
            sort="relevance",
        )
        assert changed.total == 1
        updated = discovery.add_to_my_jobs(second.id, changed.items[0].result_id)
        assert updated.outcome == "updated"
        db.refresh(job)
        assert job.status == "Preparing"
        assert job.notes == "preserve"
        assert "5 年" in job.original_jd


def test_source_failure_is_terminal_and_does_not_write_jobs() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    with Session(db_engine) as db:
        discovery = service(db, FailingAdapter([]))
        session = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(session.id)
        state = discovery.get_session(session.id)
        assert state.state == "Failed"
        assert state.error_code == "JOB_SOURCE_UNAVAILABLE"
        assert state.claude_api_calls == 0 and state.phase3_calls == 0
        assert db.scalar(select(func.count(Job.id))) == 0


def test_unexpected_source_failure_is_terminal_and_safely_mapped() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    with Session(db_engine) as db:
        discovery = service(db, UnexpectedFailingAdapter([]))
        session = discovery.create_session(
            "https://jobs.bytedance.com/experienced/position?keywords=AI", False
        )
        discovery.search(session.id)
        state = discovery.get_session(session.id)
        assert state.state == "Failed"
        assert state.error_code == "DISCOVERY_INTERNAL_ERROR"
        assert state.claude_api_calls == 0 and state.phase3_calls == 0
        assert db.scalar(select(func.count(Job.id))) == 0
