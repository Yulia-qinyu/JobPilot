import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.schemas.resume_tailoring import (
    BulletPlanItem,
    BulletValidation,
    ContextMetadata,
    DerivedEvidenceSegment,
    ExperiencePlan,
    PlanEvidence,
    SemanticValidationItemOutput,
    SemanticValidationOutput,
    TailoredBullet,
    TailoredDraft,
    TailoredExperience,
    TailoringPlan,
)
from app.services.resume_claim_validator import ResumeClaimValidator
from app.services.resume_tailoring_service import (
    InvalidEvidenceReferenceError,
    ResumeTailoringService,
)
from app.services.tailoring_evidence import (
    MeaningfulChangeDetector,
    TailoringEvidenceSegmenter,
)


def valid_pending_bullet(text: str = "A 与 C") -> TailoredBullet:
    return TailoredBullet(
        plan_item_id="item-1",
        experience_id=1,
        original_text="A、B 与 C",
        tailored_text=text,
        effective_text="A、B 与 C",
        action="Rewrite",
        evidence_source_ids=["resume_extracted:1"],
        requirement_ids=["req-1"],
        change_summary="聚焦相关事实。",
        validation=BulletValidation(
            references_valid=True,
            numbers_valid=True,
            skills_valid=True,
            ownership_valid=True,
            entities_valid=True,
            semantic_supported=False,
        ),
        state="Unverified",
        change_kind="MeaningfulRewrite",
    )


def draft_with(bullet: TailoredBullet) -> TailoredDraft:
    return TailoredDraft(
        summary="test",
        education=[],
        skills=[],
        experiences=[
            TailoredExperience(
                experience_id=1,
                organization="Example",
                title="Product Owner",
                date_range="2026.06 – 2026.08",
                bullets=[bullet],
            )
        ],
    )


def minimal_plan() -> TailoringPlan:
    context = ContextMetadata(
        experience_title="Product Owner",
        organization="Example",
        project_name="Example Product",
        date_range="2026.06 – 2026.08",
    )
    return TailoringPlan(
        plan_version="tailoring-plan-v2",
        relevant_requirements=[],
        experiences=[
            ExperiencePlan(
                experience_id=1,
                organization="Example",
                title="Product Owner",
                date_range=context.date_range,
                emphasis="Highlight",
                coverage_summary="test",
                bullet_items=[
                    BulletPlanItem(
                        plan_item_id="item-1",
                        experience_id=1,
                        source_fact_id=1,
                        original_text="A、B 与 C",
                        recommended_action="Rewrite",
                        effective_action="Rewrite",
                        omit_confirmed=False,
                        target_requirement_ids=[],
                        allowed_evidence_ids=["resume_extracted:1"],
                        context_metadata=context,
                        reason="test",
                    )
                ],
            )
        ],
        evidence=[
            PlanEvidence(
                catalog_id="resume_extracted:1",
                source_type="resume_extracted",
                source_id="1",
                text="A、B 与 C",
                context="Example · Product Owner",
            )
        ],
        section_order=["work_experience", "projects", "education", "skills"],
        skills_to_include=[],
        unsupported_requirements=[],
    )


def test_phase6_real_gold_set_baseline_is_frozen() -> None:
    path = Path(__file__).resolve().parents[1] / "evals" / "phase6_gold_set.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    bullets = [item for job in report["jobs"] for item in job["bullets"]]
    assert len(bullets) == 31
    assert sum(item["original"] == item["tailored"] for item in bullets) == 20
    assert sum(item["state"] == "FallbackOriginal" for item in bullets) == 5
    assert (
        sum(
            item["state"] == "Validated" and item["original"] != item["tailored"]
            for item in bullets
        )
        == 6
    )


def test_omission_is_supported_but_unsupported_addition_falls_back() -> None:
    service = ResumeTailoringService(Mock(), Settings())
    omitted = valid_pending_bullet("A 与 C")
    omitted_draft = draft_with(omitted)
    service._apply_semantic(
        omitted_draft,
        [SemanticValidationItemOutput(plan_item_id="item-1", unsupported_spans=[])],
    )
    assert omitted.state == "Validated"
    assert omitted.effective_text == "A 与 C"

    added = valid_pending_bullet("A、B、C 与新增 D")
    added_draft = draft_with(added)
    service._apply_semantic(
        added_draft,
        [SemanticValidationItemOutput(plan_item_id="item-1", unsupported_spans=["新增 D"])],
    )
    assert added.state == "FallbackOriginal"
    assert added.effective_text == added.original_text


def test_validator_protocol_rejects_missing_claim_diagnostic() -> None:
    service = ResumeTailoringService(Mock(), Settings())
    bullet = valid_pending_bullet("A 与 C")
    service._apply_semantic(
        draft_with(bullet),
        [
            SemanticValidationItemOutput(
                plan_item_id="item-1",
                unsupported_spans=["Missing claim about B"],
            )
        ],
    )
    assert bullet.state == "FallbackOriginal"
    assert "Missing claim about B" not in bullet.validation.violations
    assert "unsupported span" in bullet.validation.violations[0]


def test_validator_prompt_is_directional_and_receives_metadata() -> None:
    client = Mock()
    client.generate.return_value = SemanticValidationOutput(
        results=[SemanticValidationItemOutput(plan_item_id="item-1", unsupported_spans=[])]
    )
    ResumeClaimValidator(client).semantic_validate(
        [valid_pending_bullet("担任产品负责人，完成 A")], minimal_plan()
    )
    prompt = client.generate.call_args.kwargs["prompt"]
    assert "Omission is allowed" in prompt
    assert "Do not evaluate completeness" in prompt
    assert '"experience_title": "Product Owner"' in prompt


def test_title_restatement_allowed_but_responsibility_expansion_rejected() -> None:
    metadata = ContextMetadata(experience_title="Product Owner")
    validator = ResumeClaimValidator()
    restatement = validator.deterministic("担任产品负责人", [], [], metadata).validation
    expansion = validator.deterministic("全面负责产品战略和团队管理", [], [], metadata).validation
    assert not restatement.violations
    assert expansion.ownership_valid is False

    service = ResumeTailoringService(Mock(), Settings())
    bullet = valid_pending_bullet("担任产品负责人，完成 A")
    service._apply_semantic(
        draft_with(bullet),
        [
            SemanticValidationItemOutput(
                plan_item_id="item-1", unsupported_spans=["担任产品负责人，"]
            )
        ],
        plan=minimal_plan(),
    )
    assert bullet.state == "Validated"

    expanded = valid_pending_bullet("全面负责产品战略和团队管理")
    service._apply_semantic(
        draft_with(expanded),
        [
            SemanticValidationItemOutput(
                plan_item_id="item-1",
                unsupported_spans=["全面负责产品战略和团队管理"],
            )
        ],
        plan=minimal_plan(),
    )
    assert expanded.state == "FallbackOriginal"


def test_known_technology_in_evidence_is_allowed_but_jd_injection_is_not() -> None:
    validator = ResumeClaimValidator()
    assert validator.deterministic(
        "推动 RAG 文件分析", ["推动 RAG 文件分析"], []
    ).validation.skills_valid
    assert not validator.deterministic(
        "使用 AWS 部署", ["推动 RAG 文件分析"], []
    ).validation.skills_valid


@pytest.mark.parametrize(
    ("original", "tailored"),
    [
        ("开展竞品分析。", "开展竞品分析"),
        ("餐饮 / 零售 / 美业", "餐饮/零售/美业"),
        ("实现 10 万用户管理", "实现10万用户管理。"),
    ],
)
def test_formatting_only_change_is_detected(original: str, tailored: str) -> None:
    assert MeaningfulChangeDetector.is_formatting_only(original, tailored, ContextMetadata())


def test_safe_reorder_is_meaningful() -> None:
    assert not MeaningfulChangeDetector.is_formatting_only(
        "分析需求并设计 AI 产品流程",
        "围绕 AI 产品流程设计，分析并澄清用户需求",
        ContextMetadata(),
    )


def test_long_fact_segmentation_is_stable_and_separates_metadata() -> None:
    text = (
        "参与设计智能产品。负责需求分析与流程设计。"
        "协调前后端完成迭代交付。产品负责人（Product Owner）｜2026.06 – 2026.08"
    )
    segmenter = TailoringEvidenceSegmenter()
    first = segmenter.segment(
        parent_source_id="resume_extracted:28",
        text=text,
        experience_title="Project",
        organization="GoFin",
        date_range="",
    )
    second = segmenter.segment(
        parent_source_id="resume_extracted:28",
        text=text,
        experience_title="Project",
        organization="GoFin",
        date_range="",
    )
    assert first == second
    assert [item.segment_id for item in first.segments] == [
        "resume_extracted:28#seg1",
        "resume_extracted:28#seg2",
        "resume_extracted:28#seg3",
    ]
    assert all(item.parent_source_id == "resume_extracted:28" for item in first.segments)
    assert first.context_metadata.experience_title == "产品负责人（Product Owner）"
    assert first.context_metadata.date_range == "2026.06 – 2026.08"
    assert "Product Owner" not in " ".join(item.text for item in first.segments)


def test_cross_parent_segment_reference_is_rejected() -> None:
    item = minimal_plan().experiences[0].bullet_items[0]
    item.allowed_segment_ids = ["resume_extracted:2#seg1"]
    segments = {
        "resume_extracted:2#seg1": DerivedEvidenceSegment(
            segment_id="resume_extracted:2#seg1",
            parent_source_id="resume_extracted:2",
            text="Other experience",
        )
    }
    with pytest.raises(InvalidEvidenceReferenceError):
        ResumeTailoringService._validate_generated_references(
            item, ["resume_extracted:2#seg1"], segments
        )
