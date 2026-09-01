"""Aggregate Prompt / Rubric Communication Ablation Round 2A: control (Round 1B, same contract) vs
treatment (job-fit-v3-rubric-aligned-v1). No inference. No production / dataset / GT change.

Writes under backend/evals/prompt_ablation_round2a/:
  prompt_ablation_round2a_metrics.json / .csv
  prompt_ablation_round2a_comparison.md
  prompt_ablation_round2a_rule_slices.md
  prompt_ablation_round2a_model_interaction.md
  prompt_ablation_round2a_recommendation.md
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

R1B = Path("/Users/yulia/Documents/JobPilot/backend/evals/benchmark_cross_provider")
OUT = Path("/Users/yulia/Documents/JobPilot/backend/evals/prompt_ablation_round2a")

MODELS = [
    ("qwen-qwen3.8-max", "qwen3.8-max", "COST_QUALITY_CANDIDATE"),
    ("moonshot-kimi-k3", "kimi-k3", "TOP_QUALITY_CANDIDATE"),
    ("sonnet-comparable", "claude-sonnet-4-5-20250929", "INCUMBENT_CONTROL"),
]


def g(m, *path, default=None):
    cur = m
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def load(base: Path, slug: str):
    return json.loads((base / f"{'cross_provider_round1b' if base == R1B else 'prompt_ablation_round2a'}_metrics_{slug}.json").read_text())


def pc(m, cls, k):
    return g(m, "classification", "per_class", cls, k)


def support_band(d):
    if d is None:
        return "n/a"
    if d < 0.02:
        return "NOT_SUPPORTED / negligible"
    if d < 0.05:
        return "WEAKLY_SUPPORTED"
    if d < 0.10:
        return "SUPPORTED"
    return "STRONGLY_SUPPORTED"


rows = []
for slug, mid, role in MODELS:
    c = load(R1B, slug)
    t = load(OUT, slug)
    d_mf1 = round(g(t, "classification", "macro", "f1") - g(c, "classification", "macro", "f1"), 4)
    row = {
        "model": mid, "role": role,
        "control_macro_f1": g(c, "classification", "macro", "f1"),
        "treatment_macro_f1": g(t, "classification", "macro", "f1"),
        "delta_macro_f1": d_mf1,
        "hypothesis_support": support_band(d_mf1),
        "control_ecc": g(c, "system", "effective_correct_coverage"),
        "treatment_ecc": g(t, "system", "effective_correct_coverage"),
        "delta_ecc": round(g(t, "system", "effective_correct_coverage") - g(c, "system", "effective_correct_coverage"), 4),
        "control_accuracy": g(c, "classification", "accuracy"),
        "treatment_accuracy": g(t, "classification", "accuracy"),
        "delta_accuracy": round(g(t, "classification", "accuracy") - g(c, "classification", "accuracy"), 4),
        "delta_strong_r": round(pc(t, "Strong", "recall") - pc(c, "Strong", "recall"), 4),
        "delta_strong_p": round(pc(t, "Strong", "precision") - pc(c, "Strong", "precision"), 4),
        "delta_partial_p": round(pc(t, "Partial", "precision") - pc(c, "Partial", "precision"), 4),
        "delta_partial_r": round(pc(t, "Partial", "recall") - pc(c, "Partial", "recall"), 4),
        "delta_missing_r": round(pc(t, "Missing", "recall") - pc(c, "Missing", "recall"), 4),
        "control_strong_f1": pc(c, "Strong", "f1"), "treatment_strong_f1": pc(t, "Strong", "f1"),
        "control_partial_f1": pc(c, "Partial", "f1"), "treatment_partial_f1": pc(t, "Partial", "f1"),
        "control_missing_f1": pc(c, "Missing", "f1"), "treatment_missing_f1": pc(t, "Missing", "f1"),
        "control_partial_p": pc(c, "Partial", "precision"), "treatment_partial_p": pc(t, "Partial", "precision"),
        "control_strong_to_partial": g(c, "directional_errors", "Strong->Partial"),
        "treatment_strong_to_partial": g(t, "directional_errors", "Strong->Partial"),
        "delta_strong_to_partial": g(t, "directional_errors", "Strong->Partial") - g(c, "directional_errors", "Strong->Partial"),
        "control_missing_to_partial": g(c, "directional_errors", "Missing->Partial"),
        "treatment_missing_to_partial": g(t, "directional_errors", "Missing->Partial"),
        "delta_missing_to_partial": g(t, "directional_errors", "Missing->Partial") - g(c, "directional_errors", "Missing->Partial"),
        "control_partial_to_strong": g(c, "directional_errors", "Partial->Strong"),
        "treatment_partial_to_strong": g(t, "directional_errors", "Partial->Strong"),
        "control_partial_to_missing": g(c, "directional_errors", "Partial->Missing"),
        "treatment_partial_to_missing": g(t, "directional_errors", "Partial->Missing"),
        "control_confusion": g(c, "classification", "confusion_matrix", "matrix"),
        "treatment_confusion": g(t, "classification", "confusion_matrix", "matrix"),
        "control_grounding": g(c, "grounding", "grounding_rate"),
        "treatment_grounding": g(t, "grounding", "grounding_rate"),
        "control_unsupported": g(c, "grounding", "unsupported_match_rate"),
        "treatment_unsupported": g(t, "grounding", "unsupported_match_rate"),
        "control_coverage": g(c, "system", "requirement_prediction_coverage"),
        "treatment_coverage": g(t, "system", "requirement_prediction_coverage"),
        "control_job_norm": g(c, "system", "job_normalization_success"),
        "treatment_job_norm": g(t, "system", "job_normalization_success"),
        "control_ms_mae": g(c, "match_score", "mae_vs_gt_score"),
        "treatment_ms_mae": g(t, "match_score", "mae_vs_gt_score"),
        "delta_ms_mae": round(g(t, "match_score", "mae_vs_gt_score") - g(c, "match_score", "mae_vs_gt_score"), 2),
        "control_ms_median": g(c, "match_score", "median_abs_err"), "treatment_ms_median": g(t, "match_score", "median_abs_err"),
        "control_ms_max": g(c, "match_score", "max_abs_err"), "treatment_ms_max": g(t, "match_score", "max_abs_err"),
        "control_jobs_ge20": g(c, "match_score", "jobs_diff_ge_20"), "treatment_jobs_ge20": g(t, "match_score", "jobs_diff_ge_20"),
        "control_jobs_ge30": g(c, "match_score", "jobs_diff_ge_30"), "treatment_jobs_ge30": g(t, "match_score", "jobs_diff_ge_30"),
        "control_score_vs_gt": g(c, "match_score", "spearman_model_vs_gt_score"),
        "treatment_score_vs_gt": g(t, "match_score", "spearman_model_vs_gt_score"),
        "control_score_vs_hmf": g(c, "match_score", "spearman_model_vs_human_match_fit"),
        "treatment_score_vs_hmf": g(t, "match_score", "spearman_model_vs_human_match_fit"),
        "delta_score_vs_hmf": round(g(t, "match_score", "spearman_model_vs_human_match_fit") - g(c, "match_score", "spearman_model_vs_human_match_fit"), 4),
        "control_chinese_jd_macro_f1": g(c, "slice_metrics", "chinese_jd", "macro_f1"),
        "treatment_chinese_jd_macro_f1": g(t, "slice_metrics", "chinese_jd", "macro_f1"),
        "delta_chinese_jd_macro_f1": round((g(t, "slice_metrics", "chinese_jd", "macro_f1") or 0) - (g(c, "slice_metrics", "chinese_jd", "macro_f1") or 0), 4),
        "control_mean_latency_ms": g(c, "latency", "mean_ms"), "treatment_mean_latency_ms": g(t, "latency", "mean_ms"),
        "control_p90_latency_ms": g(c, "latency", "p90_ms"), "treatment_p90_latency_ms": g(t, "latency", "p90_ms"),
        "control_input_tokens": g(c, "tokens", "input"), "treatment_input_tokens": g(t, "tokens", "input"),
        "control_output_tokens": g(c, "tokens", "output"), "treatment_output_tokens": g(t, "tokens", "output"),
        "control_reasoning_tokens": g(c, "tokens", "reasoning"), "treatment_reasoning_tokens": g(t, "tokens", "reasoning"),
        "control_total_tokens": g(c, "tokens", "total"), "treatment_total_tokens": g(t, "tokens", "total"),
        "delta_total_tokens": g(t, "tokens", "total") - g(c, "tokens", "total"),
        "treatment_cost_status": g(t, "cost", "cost_status"),
        "treatment_cost_usd_30jobs": g(t, "cost", "total_usd"),
        "treatment_retries": g(t, "total_retries", default=0),
        "treatment_integrity": json.loads((OUT / f"prompt_ablation_round2a_integrity_{slug}.json").read_text())["verdict"],
        # rule-specific slices
        "slices": {},
    }
    for s in ("or_list", "technology_adjacency", "project_based_evidence", "formal_work_experience", "compound"):
        cs, ts = g(c, "slice_metrics", s) or {}, g(t, "slice_metrics", s) or {}
        row["slices"][s] = {
            "control_n_reconciled": cs.get("n_reconciled"), "control_accuracy": cs.get("accuracy"),
            "control_macro_f1": cs.get("macro_f1"), "control_errors": cs.get("errors"), "control_directional": cs.get("directional"),
            "treatment_n_reconciled": ts.get("n_reconciled"), "treatment_accuracy": ts.get("accuracy"),
            "treatment_macro_f1": ts.get("macro_f1"), "treatment_errors": ts.get("errors"), "treatment_directional": ts.get("directional"),
            "delta_accuracy": round((ts.get("accuracy") or 0) - (cs.get("accuracy") or 0), 4),
            "delta_macro_f1": (round((ts.get("macro_f1") or 0) - (cs.get("macro_f1") or 0), 4) if (ts.get("macro_f1") is not None and cs.get("macro_f1") is not None) else None),
        }
    row["control_adjacency_fp"] = g(c, "adjacency_false_positives_gt_missing_to_partial_or_strong")
    row["treatment_adjacency_fp"] = g(t, "adjacency_false_positives_gt_missing_to_partial_or_strong")
    row["control_project_over"] = g(c, "project_over_credited")
    row["treatment_project_over"] = g(t, "project_over_credited")
    row["control_project_under"] = g(c, "project_under_credited")
    row["treatment_project_under"] = g(t, "project_under_credited")
    rows.append(row)

agg = {
    "benchmark": "prompt-ablation-round2a",
    "prompt_control": "job-fit-v3-matchable-only",
    "prompt_treatment": "job-fit-v3-rubric-aligned-v1 (eval-only)",
    "prompt_hashes_file": "prompt_ablation_prompt_hashes.json",
    "dataset": "job_match_eval_dataset_v1",
    "dataset_governance": "DEVELOPMENT / MODEL-SELECTION / PROMPT-DEVELOPMENT data. NOT unbiased final evaluation. Dataset V2 remains the future held-out validation/test set and is NOT used here.",
    "ground_truth": "job-match-ground-truth-v2 (sha 52cda176...)",
    "models": ["qwen3.8-max", "kimi-k3", "claude-sonnet-4-5-20250929"],
    "control_source": "reused Round 1B same-contract results (Section A + Section D 4-field); no control rerun",
    "new_inference_calls": 90,
    "hypothesis_support_bands": {"lt_0.02": "NOT_SUPPORTED / negligible", "0.02_0.05": "WEAKLY_SUPPORTED", "0.05_0.10": "SUPPORTED", "ge_0.10": "STRONGLY_SUPPORTED"},
    "success_criteria": "clearly successful for a model iff Macro F1 improvement >= +0.05 AND no material grounding degradation AND no catastrophic reliability/coverage loss. Very strong: >= +0.10.",
    "quality_targets": {"macro_f1": 0.75, "ecc": 0.75, "strong_recall": 0.75, "strong_precision": 0.80, "partial_precision": 0.60, "missing_recall": 0.667, "grounding": 0.98, "unsupported": 0.02},
    "pre_ablation_wording": "HYPOTHESIS_STRENGTHENED (not PROMPT_CAUSE_PROVEN). This task tests the causal hypothesis.",
    "models_detail": rows,
}
(OUT / "prompt_ablation_round2a_metrics.json").write_text(json.dumps(agg, ensure_ascii=False, indent=1))

cols = ["model", "role", "control_macro_f1", "treatment_macro_f1", "delta_macro_f1", "hypothesis_support",
        "control_ecc", "treatment_ecc", "delta_ecc", "delta_accuracy",
        "delta_strong_r", "delta_strong_p", "delta_partial_p", "delta_partial_r", "delta_missing_r",
        "control_partial_p", "treatment_partial_p",
        "delta_strong_to_partial", "delta_missing_to_partial",
        "control_grounding", "treatment_grounding", "control_unsupported", "treatment_unsupported",
        "delta_ms_mae", "delta_score_vs_hmf", "delta_chinese_jd_macro_f1",
        "control_mean_latency_ms", "treatment_mean_latency_ms", "delta_total_tokens",
        "treatment_cost_status", "treatment_retries", "treatment_integrity"]
with (OUT / "prompt_ablation_round2a_metrics.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(json.dumps([{"model": r["model"], "delta_macro_f1": r["delta_macro_f1"], "support": r["hypothesis_support"],
                   "delta_ecc": r["delta_ecc"], "delta_missing_r": r["delta_missing_r"],
                   "delta_partial_p": r["delta_partial_p"], "treatment_partial_p": r["treatment_partial_p"],
                   "delta_S->P": r["delta_strong_to_partial"], "delta_M->P": r["delta_missing_to_partial"],
                   "delta_chinese_jd": r["delta_chinese_jd_macro_f1"], "delta_score_vs_hmf": r["delta_score_vs_hmf"],
                   "delta_tokens": r["delta_total_tokens"], "integrity": r["treatment_integrity"]} for r in rows],
                 ensure_ascii=False, indent=1))
print("wrote prompt_ablation_round2a_metrics.json / .csv")
