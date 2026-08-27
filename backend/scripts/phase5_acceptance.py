"""Generate privacy-safe Phase 5 funnel and human-evaluation artifacts."""

import json
import random
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Job, JobDecision, TargetRole
from app.db.session import SessionLocal
from app.repositories.profile_repository import DEFAULT_PROFILE_ID

EVAL_DIR = Path(__file__).resolve().parents[1] / "evals"
FUNNEL_PATH = EVAL_DIR / "phase5_real_funnel.json"
HUMAN_EVALUATION_PATH = EVAL_DIR / "phase5_human_evaluation.md"

BUCKETS = (
    ("worth_analyzing", "WorthAnalyzing", "Worth Analyzing", 51),
    ("low_priority", "LowPriority", "Low Priority", 52),
    ("exclude", "Exclude", "Exclude", 53),
)


class TargetRoleLike(Protocol):
    name: str
    priority: str
    effective_role_family: str


def sample(decisions: Sequence[JobDecision], value: str, seed: int) -> list[dict[str, object]]:
    candidates = sorted(
        (item for item in decisions if item.pre_match_decision == value),
        key=lambda item: item.job_id,
    )
    selected = random.Random(seed).sample(candidates, min(10, len(candidates)))
    return [
        {
            "job_id": item.job_id,
            "role": item.job.role,
            "role_family": item.effective_role_family,
            "eligibility": item.effective_eligibility_status,
            "role_fit": item.target_role_fit,
            "pre_match_decision": item.pre_match_decision,
            "reason": (
                f"明确冲突：{item.blocking_requirements[0][:180]}"
                if item.blocking_requirements
                else item.decision_reasons[0]
                if item.decision_reasons
                else ""
            ),
        }
        for item in selected
    ]


def build_report(
    decisions: Sequence[JobDecision], target_roles: Sequence[TargetRoleLike]
) -> dict[str, object]:
    eligibility = Counter(item.effective_eligibility_status for item in decisions)
    role_fit = Counter(item.target_role_fit for item in decisions)
    pre_match = Counter(item.pre_match_decision for item in decisions)
    final = Counter(item.final_decision for item in decisions if item.final_decision)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "bytedance",
        "target_roles": [
            {
                "name": role.name,
                "priority": role.priority,
                "effective_role_family": role.effective_role_family,
            }
            for role in target_roles
        ],
        "funnel": {
            "total_discovered": len(decisions),
            "no_explicit_blocker": eligibility["Eligible"],
            "possibly_eligible": eligibility["PossiblyEligible"],
            "ineligible": eligibility["Ineligible"],
            "unknown_eligibility": eligibility["Unknown"],
            "primary_target": role_fit["Primary"],
            "secondary_target": role_fit["Secondary"],
            "exploratory": role_fit["Exploratory"],
            "low_not_target_unknown": sum(
                role_fit[value] for value in ("Low", "NotTarget", "Unknown")
            ),
            "worth_analyzing": pre_match["WorthAnalyzing"],
            "low_priority": pre_match["LowPriority"],
            "excluded": pre_match["Exclude"],
            "already_deep_matched": sum(item.analysis_hash is not None for item in decisions),
            "priority": final["Priority"],
            "apply": final["Apply"],
            "consider": final["Consider"],
            "skip": final["Skip"],
            "claude_api_calls": 0,
        },
        "samples": {
            key: sample(decisions, decision, seed) for key, decision, _heading, seed in BUCKETS
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    funnel = report["funnel"]
    samples = report["samples"]
    target_roles = report["target_roles"]
    assert isinstance(funnel, dict)
    assert isinstance(samples, dict)
    assert isinstance(target_roles, list)
    generated_date = str(report["generated_at"])[:10]
    lines = [
        f"# Phase 5 Human Evaluation Sample — {generated_date}",
        "",
        (
            f"Source: current local PostgreSQL, {funnel['total_discovered']} ByteDance jobs. "
            "This report is generated from the same current-data snapshot as the JSON/stdout "
            "report and uses no Claude calls."
        ),
        "",
        "## Effective Target Roles",
        "",
    ]
    if target_roles:
        lines.extend(
            f"- {item['name']} — {item['priority']} / {item['effective_role_family']}"
            for item in target_roles
        )
    else:
        lines.append("No Target Roles are configured in the current database.")
    if target_roles and all(item["effective_role_family"] == "unknown" for item in target_roles):
        lines.extend(
            [
                "",
                (
                    "All current effective Target Roles have `role_family=unknown`; sample "
                    "buckets below reflect that current database state."
                ),
            ]
        )

    for key, decision, heading, seed in BUCKETS:
        rows = samples[key]
        assert isinstance(rows, list)
        bucket_total = int(
            funnel[
                "worth_analyzing"
                if decision == "WorthAnalyzing"
                else "low_priority"
                if decision == "LowPriority"
                else "excluded"
            ]
        )
        lines.extend(["", f"## {heading} (seed {seed})", ""])
        if not rows:
            lines.append(f"No rows available in the current database (`{bucket_total}` total).")
            continue
        if bucket_total < 10:
            lines.append(f"This bucket contains {bucket_total} current rows; all are shown.")
            lines.append("")
        lines.extend(
            [
                "| Job ID | Role | Role Family | Eligibility | Role Fit | Pre-Match Decision | Reason |",
                "|---:|---|---|---|---|---|---|",
            ]
        )
        for row in rows:
            values = [
                row["job_id"],
                row["role"],
                row["role_family"],
                row["eligibility"],
                row["role_fit"],
                row["pre_match_decision"],
                row["reason"],
            ]
            lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    lines.extend(["", "Claude calls: `0`", ""])
    return "\n".join(lines)


def write_artifacts(
    report: dict[str, object],
    funnel_path: Path = FUNNEL_PATH,
    markdown_path: Path = HUMAN_EVALUATION_PATH,
) -> None:
    funnel_path.parent.mkdir(parents=True, exist_ok=True)
    funnel_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    with SessionLocal() as db:
        decisions = list(
            db.scalars(
                select(JobDecision)
                .join(Job)
                .where(
                    Job.user_profile_id == DEFAULT_PROFILE_ID,
                    Job.source == "bytedance",
                )
                .options(selectinload(JobDecision.job))
                .order_by(JobDecision.job_id)
            ).all()
        )
        target_roles = list(
            db.scalars(
                select(TargetRole)
                .where(TargetRole.user_profile_id == DEFAULT_PROFILE_ID)
                .order_by(TargetRole.id)
            ).all()
        )
        report = build_report(decisions, target_roles)
    write_artifacts(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
