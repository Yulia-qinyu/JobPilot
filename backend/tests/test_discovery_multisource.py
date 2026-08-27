import hashlib
from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Job, JobAnalysis
from app.schemas.analysis import JDRequirements
from app.schemas.discovery import DiscoveryContextUpdate
from app.services.discovery_service import DiscoveryError, DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore
from app.services.job_sources.base import (
    ImportedJobDraft,
    SourceJobPage,
    SourceJobRecord,
    SourceSearchQuery,
)
from app.services.job_sources.bytedance import JobSourceError
from app.services.job_sources.catalog import SourceCatalog
from app.services.job_sources.registry import JobSourceRegistry


class ForbiddenCandidateContextProvider:
    calls = 0

    def load(self, _search_context):
        self.calls += 1
        raise AssertionError("Candidate context must not be read")


def engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def make_record(source: str, external_id: str, company: str, title: str) -> SourceJobRecord:
    tenant = source.split(":", 1)[1] if ":" in source else None
    provider = "greenhouse" if tenant else "bytedance"
    return SourceJobRecord(
        source=source,
        external_job_id=external_id,
        external_job_code=None,
        title=title,
        locations=("北京",) if provider == "bytedance" else ("San Francisco",),
        recruitment_type=None,
        detail_url=f"https://example.test/{source}/{external_id}",
        description="Build AI Agent product workflows.",
        requirements="At least 3 years of product experience.",
        published_date=date(2026, 8, 25),
        source_metadata={"company": company},
        provider=provider,
        tenant=tenant,
    )


class FakeMultiAdapter:
    def __init__(self, provider: str, *, fail_tenant: str | None = None):
        self.provider = self.source = provider
        self.fail_tenant = fail_tenant

    def supports(self, value: str) -> bool:
        return self.provider == "bytedance" and "bytedance.com" in value

    def parse_search_url(self, value: str) -> SourceSearchQuery:
        return SourceSearchQuery(
            source="bytedance",
            normalized_url=value,
            channel="society",
            keyword="AI Product",
            location_codes=("CT_11",),
            provider="bytedance",
        )

    def discover(self, query: SourceSearchQuery):
        if self.fail_tenant is not None and query.tenant == self.fail_tenant:
            raise JobSourceError("source timeout")
        source = query.source
        company = {
            "bytedance": "字节跳动",
            "greenhouse:scaleai": "Scale AI",
            "greenhouse:greenhouse": "Greenhouse",
            "greenhouse:anthropic": "Anthropic",
        }[source]
        record = make_record(source, f"{source}-1", company, "AI Agent Product Manager")
        yield SourceJobPage((record,), 1, 0)

    def normalize(self, record: SourceJobRecord) -> ImportedJobDraft:
        company = record.source_metadata["company"]
        original = f"{record.description}\n{record.requirements}"
        return ImportedJobDraft(
            source=record.source,
            external_job_id=record.external_job_id,
            external_job_code=None,
            company=company,
            role=record.title,
            location="、".join(record.locations),
            recruitment_type=None,
            source_url=record.detail_url,
            original_jd=original,
            structured_jd=JDRequirements(
                company=company,
                role=record.title,
                location="、".join(record.locations),
                responsibilities=[record.description],
                required_skills=[record.requirements],
            ),
            published_date=record.published_date,
            source_metadata=record.source_metadata,
            source_content_hash=hashlib.sha256(original.encode()).hexdigest(),
            provider=record.provider,
            tenant=record.tenant,
        )

    def close(self):
        return None


def test_natural_query_refinement_multisource_search_stays_ephemeral_and_adds_greenhouse() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    store = InMemoryDiscoverySessionStore()
    registry = JobSourceRegistry([FakeMultiAdapter("bytedance"), FakeMultiAdapter("greenhouse")])
    forbidden = ForbiddenCandidateContextProvider()
    with Session(db_engine, expire_on_commit=False) as db:
        service = DiscoveryService(
            db,
            store,
            registry,
            candidate_context_provider=forbidden,
            source_catalog=SourceCatalog(include_disabled_greenhouse=True),
        )
        created = service.create_session("字节 Scale AI Greenhouse AI 产品经理", False)
        assert created.state == "Ready"
        assert created.optional_refinement_groups
        assert created.claude_api_calls == 0
        ready = service.update_context(
            created.id,
            DiscoveryContextUpdate(selected_tag_ids=["ai_agent"], skip_refinement=True),
        )
        assert ready.state == "Ready"
        assert len(ready.selected_sources) == 3
        before = db.scalar(select(func.count(Job.id)))
        service.search(created.id)
        completed = service.get_session(created.id)
        assert completed.state == "Completed", completed.source_failures
        assert completed.result_count == 3
        assert db.scalar(select(func.count(Job.id))) == before == 0
        page = service.result_page(
            created.id,
            page=1,
            page_size=25,
            location=None,
            company="Scale AI",
            role_family=None,
            relevance=None,
            already_in_my_jobs=None,
            source=None,
            sort="relevance",
        )
        assert page.total == 1
        added = service.add_to_my_jobs(created.id, page.items[0].result_id)
        assert added.outcome == "created"
        job = db.get(Job, added.persistent_job_id)
        assert job.source == "greenhouse:scaleai"
        assert db.scalar(select(func.count(JobAnalysis.id))) == 0
        repeated = service.add_to_my_jobs(created.id, page.items[0].result_id)
        assert repeated.outcome == "existing"
        assert db.scalar(select(func.count(Job.id))) == 1
        assert forbidden.calls == 0


def test_one_source_failure_keeps_successes_and_marks_partial() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    registry = JobSourceRegistry(
        [FakeMultiAdapter("bytedance"), FakeMultiAdapter("greenhouse", fail_tenant="scaleai")]
    )
    with Session(db_engine) as db:
        service = DiscoveryService(
            db,
            InMemoryDiscoverySessionStore(),
            registry,
            source_catalog=SourceCatalog(include_disabled_greenhouse=True),
        )
        created = service.create_session("字节 Scale AI Greenhouse AI Agent 产品经理", False)
        if created.optional_refinement_groups:
            created = service.update_context(
                created.id, DiscoveryContextUpdate(skip_refinement=True)
            )
        service.search(created.id)
        state = service.get_session(created.id)
        assert state.state == "Partial"
        assert state.result_count == 2, state.source_failures
        assert any(item.source == "greenhouse:scaleai" for item in state.source_progress)
        assert any(item.status == "Failed" for item in state.source_progress)
        assert db.scalar(select(func.count(Job.id))) == 0


def test_unsupported_company_does_not_silently_search_other_sources() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    registry = JobSourceRegistry([FakeMultiAdapter("bytedance"), FakeMultiAdapter("greenhouse")])
    with Session(db_engine) as db:
        service = DiscoveryService(db, InMemoryDiscoverySessionStore(), registry)
        created = service.create_session("腾讯北京产品经理", False)
        assert created.state == "NeedsClarification"
        assert created.selected_sources == []
        try:
            service.update_context(
                created.id,
                DiscoveryContextUpdate(selected_tag_ids=["role_ai_product"]),
            )
        except DiscoveryError as exc:
            assert exc.code == "NO_SUPPORTED_SOURCES"
        else:  # pragma: no cover
            raise AssertionError("unsupported company must not route to unrelated sources")


def test_location_aware_routing_uses_only_supported_catalog_sources() -> None:
    db_engine = engine()
    Base.metadata.create_all(db_engine)
    registry = JobSourceRegistry([FakeMultiAdapter("bytedance"), FakeMultiAdapter("greenhouse")])
    with Session(db_engine) as db:
        service = DiscoveryService(db, InMemoryDiscoverySessionStore(), registry)
        session = service.create_session("北京 AI 产品经理", False)
        assert session.selected_sources == ["bytedance"]


def test_greenhouse_is_disabled_in_default_product_catalog_but_adapter_fixture_can_enable_it() -> None:
    assert [entry.source_key for entry in SourceCatalog().enabled()] == ["bytedance"]
    enabled = SourceCatalog(include_disabled_greenhouse=True).enabled()
    assert {entry.source_key for entry in enabled} >= {
        "bytedance",
        "greenhouse:scaleai",
        "greenhouse:greenhouse",
    }


def test_source_interleaving_prevents_large_source_from_starving_other_sources() -> None:
    byte_records = []
    green_records = []
    adapter = FakeMultiAdapter("bytedance")
    for index in range(600):
        record = make_record("bytedance", str(index), "字节跳动", f"AI Product {index}")
        byte_records.append((record, adapter.normalize(record), "large_tech"))
    green_adapter = FakeMultiAdapter("greenhouse")
    record = make_record("greenhouse:scaleai", "green-1", "Scale AI", "AI Product")
    green_records.append((record, green_adapter.normalize(record), "ai_technology"))
    ordered = DiscoveryService._interleave_by_source([*byte_records, *green_records])
    assert ordered[0][1].source == "bytedance"
    assert ordered[1][1].source == "greenhouse:scaleai"
    assert any(item[1].source == "greenhouse:scaleai" for item in ordered[:500])
