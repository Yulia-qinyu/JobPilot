import json
from pathlib import Path
from types import SimpleNamespace

from scripts.phase5_acceptance import build_report, render_markdown, sample, write_artifacts


def decision(
    job_id: int,
    pre_match: str,
    *,
    role_fit: str = "Primary",
    role_family: str = "ai_product",
) -> SimpleNamespace:
    return SimpleNamespace(
        job_id=job_id,
        job=SimpleNamespace(role=f"Role {job_id}"),
        effective_role_family=role_family,
        effective_eligibility_status="Eligible",
        target_role_fit=role_fit,
        pre_match_decision=pre_match,
        blocking_requirements=[],
        decision_reasons=[f"Reason {job_id}"],
        analysis_hash=None,
        final_decision=None,
    )


def target_role(family: str) -> SimpleNamespace:
    return SimpleNamespace(
        name="AI Product Manager", priority="primary", effective_role_family=family
    )


def test_configured_target_roles_generate_ten_worth_analyzing_samples() -> None:
    decisions = [decision(index, "WorthAnalyzing") for index in range(1, 13)]
    report = build_report(decisions, [target_role("ai_product")])

    assert report["funnel"]["worth_analyzing"] == 12
    assert len(report["samples"]["worth_analyzing"]) == 10
    assert "role_family=unknown" not in render_markdown(report)


def test_unknown_target_roles_generate_truthful_no_row_state() -> None:
    decisions = [decision(index, "LowPriority", role_fit="Unknown") for index in range(1, 4)]
    report = build_report(decisions, [target_role("unknown")])
    markdown = render_markdown(report)

    assert report["funnel"]["worth_analyzing"] == 0
    assert report["samples"]["worth_analyzing"] == []
    assert "All current effective Target Roles have `role_family=unknown`" in markdown
    assert "No rows available in the current database (`0` total)." in markdown


def test_sampling_is_seeded_and_small_buckets_show_all_rows() -> None:
    decisions = [decision(index, "Exclude") for index in range(1, 7)]

    assert sample(decisions, "Exclude", 53) == sample(list(reversed(decisions)), "Exclude", 53)
    report = build_report(decisions, [target_role("ai_product")])
    markdown = render_markdown(report)
    assert len(report["samples"]["exclude"]) == 6
    assert "This bucket contains 6 current rows; all are shown." in markdown


def test_written_json_and_markdown_use_the_same_report(tmp_path: Path) -> None:
    decisions = [decision(index, "WorthAnalyzing") for index in range(1, 11)]
    report = build_report(decisions, [target_role("ai_product")])
    funnel_path = tmp_path / "funnel.json"
    markdown_path = tmp_path / "sample.md"

    write_artifacts(report, funnel_path, markdown_path)

    assert json.loads(funnel_path.read_text(encoding="utf-8")) == report
    markdown = markdown_path.read_text(encoding="utf-8")
    for row in report["samples"]["worth_analyzing"]:
        assert f"| {row['job_id']} |" in markdown
    assert report["funnel"]["claude_api_calls"] == 0
    assert "Claude calls: `0`" in markdown
