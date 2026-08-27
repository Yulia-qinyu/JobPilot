from datetime import UTC, datetime, timedelta

from app.schemas.discovery import DiscoverySearchContext
from app.services.company_source_resolver import CompanySourceResolver
from app.services.discovery_intent import DiscoveryIntentParser
from app.services.job_sources.catalog import SourceCatalog


def context(query: str) -> DiscoverySearchContext:
    parsed = DiscoveryIntentParser().parse(query)
    now = datetime.now(UTC)
    return DiscoverySearchContext(
        session_id="test",
        input_kind="natural_language",
        raw_input=query,
        explicit_constraints=parsed.constraints,
        include_terms=parsed.include_terms,
        exclusions=parsed.exclusions,
        freeform_terms=parsed.freeform_terms,
        explicit_concepts=parsed.explicit_concepts,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


def test_no_company_selects_all_enabled_domestic_sources() -> None:
    plan = CompanySourceResolver(SourceCatalog()).plan(context("北京 AI 产品经理"))
    assert {item.company_id for item in plan.selected_sources} == {"bytedance"}
    assert {item.channel for item in plan.selected_sources} == {
        "campus",
        "experienced",
    }
    assert plan.coverage_status == "supported"


def test_company_aliases_resolve_to_the_same_canonical_company() -> None:
    resolver = CompanySourceResolver(SourceCatalog())
    for query in ("字节 AI 产品经理", "字节跳动 AI 产品经理", "ByteDance AI Product"):
        plan = resolver.plan(context(query))
        assert plan.requested_companies == ["字节跳动"]
        assert {item.company_id for item in plan.selected_sources} == {"bytedance"}


def test_unsupported_and_partial_coverage_are_honest() -> None:
    resolver = CompanySourceResolver(SourceCatalog())
    unsupported = resolver.plan(context("小米 AI 产品经理 北京"))
    partial = resolver.plan(context("字节 小米 AI 产品经理 北京"))
    assert unsupported.coverage_status == "unsupported"
    assert unsupported.unsupported_companies == ["小米"]
    assert unsupported.selected_sources == []
    assert partial.coverage_status == "partial"
    assert partial.unsupported_companies == ["小米"]
    assert {item.company_id for item in partial.selected_sources} == {"bytedance"}


def test_recruitment_type_controls_bytedance_channel_plan() -> None:
    resolver = CompanySourceResolver(SourceCatalog())
    campus = resolver.plan(context("北京 应届 AI 产品经理"))
    experienced = resolver.plan(context("北京 社招 AI 产品经理"))
    assert [item.channel for item in campus.selected_sources] == ["campus"]
    assert [item.channel for item in experienced.selected_sources] == ["experienced"]
