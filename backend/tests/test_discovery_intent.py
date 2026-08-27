from app.services.claude_client import ClaudeServiceError
from app.services.discovery_intent import (
    ClaudeIntentConstraints,
    ClaudeIntentOutput,
    ClaudeRefinementOption,
    ClaudeRefinementPlan,
    DiscoveryIntentParser,
)
from app.services.discovery_tags import DiscoveryTagCatalog


class FakeClaudeClient:
    def __init__(self) -> None:
        self.calls = 0
        self.last_call_metrics = {"input_tokens": 120, "output_tokens": 80}

    def generate(self, **_kwargs):
        self.calls += 1
        return ClaudeIntentOutput(
            explicit_constraints=ClaudeIntentConstraints(
                role_terms=["AI product"],
                role_families=["ai_product", "invented_family"],
                locations=["北京"],
                companies=[],
                company_groups=[],
                job_functions=["investment"],
                industries=["互联网"],
                domains=["primary_market"],
                seniority=[],
                recruitment_types=[],
            ),
            include_terms=["出海", "电商"],
            exclusions=[],
            freeform_terms=[],
            refinement_dimension_ids=["business_scenario", "invented_dimension"],
            ambiguities=[],
        )


class FailingClaudeClient(FakeClaudeClient):
    def generate(self, **_kwargs):
        self.calls += 1
        raise ClaudeServiceError("temporary")


class MalformedPlanClient(FakeClaudeClient):
    def generate(self, **_kwargs):
        self.calls += 1
        return ClaudeIntentOutput(
            explicit_constraints=ClaudeIntentConstraints(),
            refinement_plans=[
                ClaudeRefinementPlan(
                    dimension_id="invented_dimension",
                    question="x" * 200,
                    required=True,
                    options=[
                        ClaudeRefinementOption(
                            id="same", label="A", normalized_value="", freeform_value=""
                        ),
                        ClaudeRefinementOption(
                            id="same", label="B", normalized_value="", freeform_value=""
                        ),
                        ClaudeRefinementOption(
                            id="third", label="C", normalized_value="", freeform_value=""
                        ),
                    ],
                )
            ]
        )


class ValidPlanClient(FakeClaudeClient):
    def generate(self, **_kwargs):
        self.calls += 1
        return ClaudeIntentOutput(
            explicit_constraints=ClaudeIntentConstraints(
                job_functions=["investment"], domains=["primary_market", "technology"]
            ),
            refinement_plans=[
                ClaudeRefinementPlan(
                    dimension_id="domain",
                    question="更关注哪类科技投资？",
                    required=False,
                    options=[
                        ClaudeRefinementOption(
                            id="enterprise",
                            label="企业科技",
                            normalized_value="technology",
                            freeform_value="",
                        ),
                        ClaudeRefinementOption(
                            id="consumer",
                            label="消费科技",
                            normalized_value="",
                            freeform_value="消费科技",
                        ),
                        ClaudeRefinementOption(
                            id="any",
                            label="不限",
                            normalized_value="",
                            freeform_value="不限",
                        ),
                    ],
                )
            ],
        )


def test_simple_queries_are_deterministic_and_do_not_call_claude() -> None:
    client = FakeClaudeClient()
    parser = DiscoveryIntentParser(client)  # type: ignore[arg-type]
    parsed = parser.parse("北京 AI 产品经理")
    assert parsed.method == "deterministic"
    assert parsed.claude_calls == 0 and client.calls == 0
    assert parsed.constraints.locations == ["北京"]
    assert parsed.constraints.role_families == ["ai_product"]
    english = parser.parse("AI Product Manager")
    assert english.constraints.role_families == ["ai_product"]


def test_deterministic_parser_handles_recruitment_tags_and_exclusions() -> None:
    parsed = DiscoveryIntentParser().parse("北京应届 AI Agent 产品经理，不要运营和解决方案")
    assert parsed.constraints.recruitment_types == ["graduate"]
    assert parsed.constraints.role_families == ["ai_product"]
    assert "Agent" in parsed.include_terms
    assert any("运营" in value for value in parsed.exclusions)
    assert "ai_agent" in parsed.selected_tag_ids


def test_fintech_multi_concept_and_seniority_queries() -> None:
    parser = DiscoveryIntentParser()
    fintech = parser.parse("上海 FinTech 产品经理")
    seniority = parser.parse("AI 产品经理，不看高级和资深岗")
    assert fintech.constraints.role_families == ["fintech_product"]
    assert fintech.constraints.locations == ["上海"]
    assert "高级/资深" in seniority.exclusions


def test_complex_query_uses_at_most_one_claude_call_and_drops_unknown_taxonomy() -> None:
    client = FakeClaudeClient()
    parsed = DiscoveryIntentParser(client).parse("我想做偏一级市场、科技方向的投资岗位")  # type: ignore[arg-type]
    assert client.calls == parsed.claude_calls == 1
    assert parsed.method == "hybrid"
    assert parsed.constraints.role_families == ["ai_product"]
    assert parsed.constraints.job_functions == ["investment"]
    assert parsed.constraints.domains == ["primary_market", "technology"]
    assert parsed.input_tokens == 120 and parsed.output_tokens == 80


def test_claude_failure_falls_back_to_deterministic_without_second_call() -> None:
    client = FailingClaudeClient()
    parsed = DiscoveryIntentParser(client).parse("我想做偏一级市场、科技方向的投资岗位")  # type: ignore[arg-type]
    assert client.calls == parsed.claude_calls == 1
    assert parsed.method == "deterministic"
    assert parsed.constraints.job_functions == ["investment"]


def test_vague_ai_work_is_marked_ambiguous() -> None:
    parsed = DiscoveryIntentParser().parse("帮我找 AI 工作")
    assert "job_function" in parsed.ambiguities
    assert parsed.required_refinement_dimension_ids == []
    assert parsed.required_refinement_groups[0].id == "job_function"
    assert "AI 岗位" in parsed.required_refinement_groups[0].label
    assert parsed.optional_refinement_dimension_ids == []


def test_explicit_fine_grained_concepts_survive_into_intent() -> None:
    parser = DiscoveryIntentParser()
    cases = {
        "我想看看大模型平台方向": {"llm_application", "ai_platform"},
        "多模态 AI 产品": {"multimodal"},
        "AIGC 内容产品经理": {"aigc", "content_creator"},
        "ToB AI 产品经理": {"enterprise_tob"},
        "增长产品经理 电商": {"ecommerce"},
        "AI 产品，出海和电商都可以": {"international", "ecommerce"},
    }
    for query, expected in cases.items():
        parsed = parser.parse(query)
        assert expected.issubset(set(parsed.selected_tag_ids)), query
        assert parsed.include_terms, query
    assert parser.parse("多模态 AI 产品").constraints.role_families == ["ai_product"]
    assert parser.parse("增长产品经理 电商").constraints.role_families == ["growth_product"]


def test_clear_queries_only_offer_optional_refinement() -> None:
    parser = DiscoveryIntentParser()
    clear = parser.parse("北京 AI Agent 产品经理 大厂")
    graduate = parser.parse("北京应届 AI 产品，不要运营")
    generic = parser.parse("腾讯北京产品")
    assert clear.required_refinement_dimension_ids == []
    assert clear.optional_refinement_dimension_ids
    assert graduate.required_refinement_dimension_ids == []
    assert graduate.optional_refinement_dimension_ids
    assert generic.required_refinement_dimension_ids == ["role"]
    assert generic.constraints.locations == ["北京"]
    assert generic.constraints.companies == ["腾讯"]


def test_recruitment_channel_aliases_are_normalized() -> None:
    parser = DiscoveryIntentParser()
    for query in ("北京秋招产品经理", "北京校园招聘产品经理", "new grad product manager"):
        assert parser.parse(query).constraints.recruitment_types == ["graduate"]
    for query in ("北京社会招聘产品经理", "北京有经验岗位产品经理"):
        assert parser.parse(query).constraints.recruitment_types == ["experienced"]


def test_xiaomi_is_preserved_for_unsupported_source_honesty() -> None:
    parsed = DiscoveryIntentParser().parse("小米 AI 产品经理 北京")
    assert parsed.constraints.companies == ["小米"]
    assert parsed.constraints.locations == ["北京"]
    assert parsed.constraints.role_families == ["ai_product"]


def test_tag_catalog_is_versioned_stable_and_validates_selection() -> None:
    catalog = DiscoveryTagCatalog()
    assert catalog.version == "discovery-tags-v1"
    assert catalog.get("ai_agent").label == "AI Agent"  # type: ignore[union-attr]
    assert catalog.get("agent_platform").parent_id == "ai_agent"  # type: ignore[union-attr]
    assert catalog.get("role_ai_product").dimension == "role"  # type: ignore[union-attr]
    assert catalog.validate(["graduate", "experienced", "unknown", "ai_agent"]) == [
        "graduate",
        "ai_agent",
    ]
    child = catalog.child_groups(["ai_agent"])
    assert child[0].id == "agent_subtype"


def test_generalized_queries_preserve_function_industry_domain_and_freeform() -> None:
    parser = DiscoveryIntentParser()
    banking = parser.parse("北京 银行 应届 投资")
    analytics = parser.parse("上海 数据分析 电商")
    consulting = parser.parse("北京 战略咨询 应届")
    algorithm = parser.parse("深圳 大模型 算法")
    marketing = parser.parse("北京 消费品 市场营销")
    unknown = parser.parse("量化一级市场投资 北京")

    assert banking.constraints.job_functions == ["investment"]
    assert banking.constraints.industries == ["banking"]
    assert banking.constraints.recruitment_types == ["graduate"]
    assert banking.optional_refinement_groups[0].id == "investment_subdomain"
    assert analytics.constraints.job_functions == ["data_analytics"]
    assert analytics.constraints.industries == ["ecommerce"]
    assert consulting.constraints.job_functions == ["strategy_consulting"]
    assert algorithm.constraints.job_functions == ["algorithm_research"]
    assert "llm" in algorithm.constraints.domains
    assert marketing.constraints.job_functions == ["marketing"]
    assert marketing.constraints.industries == ["consumer_goods"]
    assert {item.raw_text for item in unknown.explicit_concepts} >= {"量化", "一级市场"}


def test_finance_without_job_function_requires_only_function_clarification() -> None:
    parsed = DiscoveryIntentParser().parse("帮我找金融工作")
    assert parsed.constraints.industries == ["financial_services"]
    assert parsed.ambiguities == ["job_function"]
    assert parsed.required_refinement_groups[0].id == "job_function"
    assert "金融岗位" in parsed.required_refinement_groups[0].label


def test_malformed_semantic_refinement_is_dropped_without_second_call() -> None:
    client = MalformedPlanClient()
    parsed = DiscoveryIntentParser(client).parse("量化一级市场投资 北京")  # type: ignore[arg-type]
    assert client.calls == parsed.claude_calls == 1
    assert parsed.required_refinement_groups == []
    assert all(group.source == "catalog" for group in parsed.optional_refinement_groups)


def test_semantic_planner_produces_bounded_session_local_refinement() -> None:
    client = ValidPlanClient()
    parsed = DiscoveryIntentParser(client).parse("量化一级市场投资 北京")  # type: ignore[arg-type]
    assert client.calls == parsed.claude_calls == 1
    assert parsed.method == "hybrid"
    assert len(parsed.optional_refinement_groups) == 1
    group = parsed.optional_refinement_groups[0]
    assert group.source == "semantic_planner"
    assert group.required is False
    assert len(group.tags) == 3
    assert all(tag.id.startswith("semantic:domain:") for tag in group.tags)
