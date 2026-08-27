import hashlib

from app.schemas.analysis import JDRequirements
from app.schemas.discovery import DiscoveryExplicitConstraints, DiscoverySearchContext
from app.services.discovery_ranking import derive_search_relevance, extract_explicit_hard_signals
from app.services.job_sources.base import ImportedJobDraft


def context(*, exclusions=None, include=None) -> DiscoverySearchContext:
    return DiscoverySearchContext(
        session_id="session",
        input_kind="natural_language",
        raw_input="北京 AI Agent 产品经理，不要运营",
        explicit_constraints=DiscoveryExplicitConstraints(
            role_terms=["AI 产品经理"], role_families=["ai_product"], locations=["北京"]
        ),
        include_terms=include or ["Agent"],
        exclusions=exclusions or [],
        created_at="2026-08-25T00:00:00Z",
        expires_at="2026-08-25T01:00:00Z",
    )


def draft(role="AI Agent 产品经理", requirement="至少 5 年产品经验") -> ImportedJobDraft:
    original = f"负责 Agent 产品。\n{requirement}"
    return ImportedJobDraft(
        source="bytedance",
        external_job_id="1",
        external_job_code=None,
        company="字节跳动",
        role=role,
        location="北京",
        recruitment_type="社招",
        source_url="https://jobs.bytedance.com/job/1",
        original_jd=original,
        structured_jd=JDRequirements(
            role=role,
            company="字节跳动",
            location="北京",
            responsibilities=["负责 Agent 产品"],
            required_skills=[requirement],
        ),
        published_date=None,
        source_metadata={},
        source_content_hash=hashlib.sha256(original.encode()).hexdigest(),
    )


def test_structured_hard_signal_contains_type_value_and_source_text() -> None:
    signals = extract_explicit_hard_signals(draft())
    assert len(signals) == 1
    assert signals[0].type == "experience_years"
    assert signals[0].operator == ">=" and signals[0].value == 5
    assert signals[0].display == "明确要求 5+ 年经验"
    assert "至少 5 年" in signals[0].source_text


def test_explicit_exclusion_is_strong_but_unknown_is_not_negative() -> None:
    excluded = derive_search_relevance(
        context(exclusions=["运营"]),
        draft("产品运营（AI方向）"),
        "product_operations",
        extract_explicit_hard_signals(draft()),
    )
    ordinary = derive_search_relevance(
        context(),
        draft(requirement="熟悉 AI 产品优先"),
        "ai_product",
        [],
        company_group="large_tech",
    )
    assert excluded.excluded_by_current_search is True
    assert excluded.relevance_band == "Low"
    assert any(item.kind == "excluded" for item in excluded.reason_items)
    assert ordinary.excluded_by_current_search is False
    assert ordinary.relevance_band == "High"
    assert any(item.kind == "unknown" for item in ordinary.reason_items)


def test_explicit_ai_product_role_cannot_be_rescued_by_agent_keyword() -> None:
    cases = {
        "AI Product Manager": ("ai_product", "High"),
        "Agent 产品经理": ("ai_product", "High"),
        "Senior Product Manager, Agent Platform": ("general_product", "Medium"),
        "Engineering Manager, Agent Cloud Platform": ("engineering", "Low"),
        "AI Infrastructure Engineer, Agent Runtime": ("engineering", "Low"),
        "Applied AI Engineer": ("engineering", "Low"),
        "Agent 推荐算法工程师": ("algorithm", "Low"),
    }
    for role, (family, expected) in cases.items():
        ranked = derive_search_relevance(
            context(include=["Agent"]), draft(role, "熟悉 Agent 产品优先"), family, []
        )
        assert ranked.relevance_band == expected, role


def test_requested_engineering_family_is_not_globally_penalized() -> None:
    engineering_context = context().model_copy(
        update={
            "explicit_constraints": DiscoveryExplicitConstraints(
                role_terms=["AI Engineer"], role_families=["engineering"]
            )
        }
    )
    ranked = derive_search_relevance(
        engineering_context,
        draft("Applied AI Engineer", "3+ years required experience"),
        "engineering",
        [],
    )
    assert ranked.relevance_band == "High"


def test_hard_signals_ignore_responsibilities_and_use_compact_displays() -> None:
    responsibilities = (
        "As a Production AI Ops Manager, you will design and develop production systems."
    )
    assert extract_explicit_hard_signals(draft(requirement=responsibilities)) == []
    assert extract_explicit_hard_signals(
        draft(requirement="You will design and develop reliable AI services")
    ) == []
    years = extract_explicit_hard_signals(
        draft(requirement="Candidates must have at least 6 years of product experience")
    )
    degree = extract_explicit_hard_signals(draft(requirement="Bachelor's degree required"))
    assert years[0].display == "明确要求 6+ 年经验"
    assert degree[0].display == "明确要求本科及以上学历"


def test_generalized_job_function_is_stronger_than_topic_overlap() -> None:
    investment_context = context().model_copy(
        update={
            "explicit_constraints": DiscoveryExplicitConstraints(
                locations=["北京"],
                job_functions=["investment"],
                industries=["banking"],
            ),
            "include_terms": ["科技"],
        }
    )
    investment = derive_search_relevance(
        investment_context,
        draft("科技投资经理", "负责银行科技领域投资研究"),
        "unknown",
        [],
    )
    product = derive_search_relevance(
        investment_context,
        draft("金融科技产品经理", "负责银行科技产品"),
        "fintech_product",
        [],
    )
    assert investment.relevance_band == "High"
    assert product.relevance_band == "Low"
    assert any(
        item.code == "job_function_mismatch" for item in product.reason_items
    )


def test_generalized_unknown_function_remains_conservative_not_mismatch() -> None:
    marketing_context = context().model_copy(
        update={
            "explicit_constraints": DiscoveryExplicitConstraints(
                job_functions=["marketing"], industries=["consumer_goods"]
            )
        }
    )
    ranked = derive_search_relevance(
        marketing_context,
        draft("消费品管培生", "参与品牌与市场项目"),
        "unknown",
        [],
    )
    assert not any(
        item.code == "job_function_mismatch" for item in ranked.reason_items
    )
