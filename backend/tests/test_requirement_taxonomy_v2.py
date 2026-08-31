from app.schemas.analysis import (
    JDRequirementsOutput,
    JDStructuredRequirementOutput,
)
from app.services.evidence_catalog import canonical_hash
from app.services.jd_parser import JDParser
from app.services.requirement_catalog import RequirementCatalogBuilder


def output_for(*requirements: JDStructuredRequirementOutput) -> JDRequirementsOutput:
    return JDRequirementsOutput(
        role="",
        company="",
        location="",
        recruitment_type="",
        published_date="",
        role_summary="测试岗位",
        key_requirements=[],
        knowledge_topics=["不应成为 V2 source of truth"],
        responsibilities=[],
        required_skills=[],
        preferred_skills=[],
        ai_requirements=[],
        product_requirements=[],
        technical_requirements=[],
        domain_requirements=[],
        requirements=list(requirements),
    )


def suggestion(
    source_text: str,
    normalized: str,
    requirement_type: str,
    *,
    importance: str = "Important",
    category: str = "none",
    topics: list[str] | None = None,
    section: str = "requirements",
) -> JDStructuredRequirementOutput:
    return JDStructuredRequirementOutput(
        source_text=source_text,
        normalized_requirement=normalized,
        source_section=section,
        requirement_type=requirement_type,
        importance=importance,
        eligibility_category=category,
        knowledge_topics=topics or [],
    )


def test_v2_edge_case_taxonomy_and_subjective_exclusion() -> None:
    jd = (
        "熟练使用 SQL。深入理解 LLM、Agent、RAG 原理及能力边界。"
        "3年以上 AI 产品经验。有金融行业经验优先。对 AI 有极高热情。"
    )
    parsed = JDParser._to_requirements(
        output_for(
            suggestion("熟练使用 SQL", "熟练使用 SQL", "matchable"),
            suggestion(
                "深入理解 LLM、Agent、RAG 原理及能力边界",
                "理解 LLM、Agent、RAG 原理及能力边界",
                "knowledge",
                topics=["LLM 原理", "Agent 架构", "RAG 原理"],
            ),
            suggestion(
                "3年以上 AI 产品经验",
                "3年以上 AI 产品经验",
                "eligibility",
                category="experience_years",
            ),
            # A duplicate matchable suggestion from the exact same duration clause is rejected.
            suggestion("3年以上 AI 产品经验", "AI 产品经验", "matchable"),
            suggestion(
                "有金融行业经验优先",
                "金融行业经验",
                "matchable",
                importance="Preferred",
                section="preferred",
            ),
            suggestion("对 AI 有极高热情", "对 AI 有极高热情", "subjective"),
        ),
        jd,
    )
    assert [item.requirement_type for item in parsed.requirements] == [
        "matchable",
        "knowledge",
        "eligibility",
        "matchable",
    ]
    assert parsed.requirements[2].importance == "Critical"
    assert parsed.requirements[3].importance == "Preferred"
    assert parsed.knowledge_topics == ["LLM 原理", "Agent 架构", "RAG 原理"]
    assert parsed.subjective_expectations == ["对 AI 有极高热情"]


def test_compound_explicit_agent_requirement_can_split() -> None:
    source = "有 Agent 产品经验，并深入理解 Agent 架构"
    parsed = JDParser._to_requirements(
        output_for(
            suggestion("有 Agent 产品经验", "Agent 产品经验", "matchable"),
            suggestion(
                "深入理解 Agent 架构",
                "理解 Agent 架构",
                "knowledge",
                topics=["Agent 架构"],
            ),
        ),
        source,
    )
    assert {item.requirement_type for item in parsed.requirements} == {
        "matchable",
        "knowledge",
    }


def test_practical_rag_requirement_remains_matchable() -> None:
    source = "熟悉大模型并有 RAG 实践经验"
    parsed = JDParser._to_requirements(
        output_for(suggestion(source, "大模型与 RAG 实践经验", "matchable")),
        source,
    )
    assert parsed.requirements[0].requirement_type == "matchable"


def test_unsupported_source_text_is_not_admitted() -> None:
    parsed = JDParser._to_requirements(
        output_for(suggestion("有 Agent 项目经验", "Agent 项目经验", "matchable")),
        "深入理解 Agent 原理",
    )
    assert parsed.requirements == []


def test_stable_ids_and_v2_hash_ignore_display_order() -> None:
    jd = "熟练使用 SQL。理解 RAG 原理。"
    first = JDParser._to_requirements(
        output_for(
            suggestion("熟练使用 SQL", "熟练使用 SQL", "matchable"),
            suggestion("理解 RAG 原理", "理解 RAG 原理", "knowledge", topics=["RAG"]),
        ),
        jd,
    )
    second = first.model_copy(
        update={
            "role_summary": "完全不同的展示摘要",
            "knowledge_topics": list(reversed(first.knowledge_topics)),
            "requirements": list(reversed(first.requirements)),
        }
    )
    assert {item.requirement_id for item in first.requirements} == {
        item.requirement_id for item in second.requirements
    }
    builder = RequirementCatalogBuilder()
    assert builder.structured_jd_hash(first) == builder.structured_jd_hash(second)


def test_v2_catalog_contains_matchable_only_and_legacy_hash_is_unchanged() -> None:
    parsed = JDParser._to_requirements(
        output_for(
            suggestion("熟练使用 SQL", "熟练使用 SQL", "matchable"),
            suggestion("2027届本科及以上", "2027届本科及以上", "eligibility", category="graduation_cohort"),
            suggestion("理解 RAG 原理", "理解 RAG 原理", "knowledge", topics=["RAG"]),
        ),
        "熟练使用 SQL。2027届本科及以上。理解 RAG 原理。",
    )
    catalog = RequirementCatalogBuilder().build(parsed)
    assert [item.text for item in catalog.requirements] == ["熟练使用 SQL"]

    legacy = parsed.model_copy(
        update={
            "requirement_taxonomy_version": "legacy-v1",
            "requirements": [],
            "subjective_expectations": [],
        }
    )
    old_payload = legacy.model_dump(
        mode="json",
        exclude={"requirement_taxonomy_version", "requirements", "subjective_expectations"},
    )
    assert RequirementCatalogBuilder.structured_jd_hash(legacy) == canonical_hash(old_payload)
