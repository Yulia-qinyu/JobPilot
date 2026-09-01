"""Aggregate Prompt Refinement Round 2B: for kimi-k3 and qwen3.8-max show
  A = Round 1B control (job-fit-v3-matchable-only)
  B = Round 2A full rubric (job-fit-v3-rubric-aligned-v1)   [rejected]
  C = Round 2B refined (job-fit-v3-rubric-refined-v2)
No inference. No production / dataset / GT change.
"""
from __future__ import annotations

import json
from pathlib import Path

R1B = Path("/Users/yulia/Documents/JobPilot/backend/evals/benchmark_cross_provider")
R2A = Path("/Users/yulia/Documents/JobPilot/backend/evals/prompt_ablation_round2a")
R2B = Path("/Users/yulia/Documents/JobPilot/backend/evals/prompt_refinement_round2b")

MODELS = [("moonshot-kimi-k3", "kimi-k3"), ("qwen-qwen3.8-max", "qwen3.8-max")]


def g(m, *p, d=None):
    c = m
    for k in p:
        if isinstance(c, dict) and k in c:
            c = c[k]
        else:
            return d
    return c


def load(base, slug, prefix):
    return json.loads((base / f"{prefix}_metrics_{slug}.json").read_text())


def pc(m, cls, k):
    return g(m, "classification", "per_class", cls, k)


def snap(m):
    return {
        "macro_f1": g(m, "classification", "macro", "f1"),
        "ecc": g(m, "system", "effective_correct_coverage"),
        "accuracy": g(m, "classification", "accuracy"),
        "coverage": g(m, "system", "requirement_prediction_coverage"),
        "job_norm": g(m, "system", "job_normalization_success"),
        "strong": [pc(m, "Strong", "precision"), pc(m, "Strong", "recall"), pc(m, "Strong", "f1")],
        "partial": [pc(m, "Partial", "precision"), pc(m, "Partial", "recall"), pc(m, "Partial", "f1")],
        "missing": [pc(m, "Missing", "precision"), pc(m, "Missing", "recall"), pc(m, "Missing", "f1")],
        "confusion": g(m, "classification", "confusion_matrix", "matrix"),
        "S_to_P": g(m, "directional_errors", "Strong->Partial"),
        "M_to_P": g(m, "directional_errors", "Missing->Partial"),
        "P_to_S": g(m, "directional_errors", "Partial->Strong"),
        "P_to_M": g(m, "directional_errors", "Partial->Missing"),
        "grounding": g(m, "grounding", "grounding_rate"),
        "unsupported": g(m, "grounding", "unsupported_match_rate"),
        "ms_mae": g(m, "match_score", "mae_vs_gt_score"),
        "score_vs_gt": g(m, "match_score", "spearman_model_vs_gt_score"),
        "score_vs_hmf": g(m, "match_score", "spearman_model_vs_human_match_fit"),
        "chinese_jd_mf1": g(m, "slice_metrics", "chinese_jd", "macro_f1"),
        "mean_latency_ms": g(m, "latency", "mean_ms"),
        "total_tokens": g(m, "tokens", "total"),
        "reasoning_tokens": g(m, "tokens", "reasoning"),
        "slices": {s: {"n_reconciled": g(m, "slice_metrics", s, "n_reconciled"),
                       "accuracy": g(m, "slice_metrics", s, "accuracy"),
                       "macro_f1": g(m, "slice_metrics", s, "macro_f1"),
                       "errors": g(m, "slice_metrics", s, "errors")}
                   for s in ("technology_adjacency", "project_based_evidence",
                             "formal_work_experience", "or_list", "compound")},
        "adjacency_fp": g(m, "adjacency_false_positives_gt_missing_to_partial_or_strong"),
        "project_over": g(m, "project_over_credited"),
        "project_under": g(m, "project_under_credited"),
    }


def support(d):
    if d is None:
        return "n/a"
    if d < 0.02:
        return "NOT_SUPPORTED / negligible"
    if d < 0.05:
        return "WEAKLY_SUPPORTED"
    if d < 0.10:
        return "SUPPORTED"
    return "STRONGLY_SUPPORTED"


CONTROL = {
    "kimi-k3": {"macro_f1": 0.7396, "ecc": 0.74, "coverage": "100/100", "job_norm": "30/30",
                "chinese_jd_mf1": 0.7515, "score_vs_hmf": 0.723},
    "qwen3.8-max": {"macro_f1": 0.7016, "ecc": 0.71, "coverage": "100/100", "job_norm": "30/30",
                    "chinese_jd_mf1": 0.7087, "score_vs_hmf": 0.609},
}

out = {"benchmark": "prompt-refinement-round2b",
       "prompt_a_control": "job-fit-v3-matchable-only",
       "prompt_b_rejected": "job-fit-v3-rubric-aligned-v1 (Round 2A; OR-list + compound rules)",
       "prompt_c_refined": "job-fit-v3-rubric-refined-v2 (Round 2B; adjacency + project-vs-work + calibration only)",
       "prompt_c_instruction_sha256": json.loads((R2B / "prompt_refinement_prompt_hashes.json").read_text())["prompt_c_instruction_block_sha256"],
       "models": ["kimi-k3", "qwen3.8-max"],
       "control_source": "reused Round 1B same-contract results; NO control rerun",
       "new_inference_calls": 60,
       "dataset_governance": "FINAL Dataset V1 prompt-development iteration. Development-set only. Dataset V2 held-out, NOT used.",
       "prompt_bottleneck_status": "REAL_BUT_PARTIAL_LEVER (Round 2A causally demonstrated rubric communication affects behaviour; NOT the sole/dominant cause; no ~93%-causal claim).",
       "hypothesis_support_bands": {"lt_0.02": "NOT_SUPPORTED", "0.02_0.05": "WEAKLY_SUPPORTED", "0.05_0.10": "SUPPORTED", "ge_0.10": "STRONGLY_SUPPORTED"},
       "models_detail": []}

for slug, name in MODELS:
    A = snap(load(R1B, slug, "cross_provider_round1b"))
    B = snap(load(R2A, slug, "prompt_ablation_round2a"))
    C = snap(load(R2B, slug, "prompt_refinement_round2b"))
    itC = json.loads((R2B / f"prompt_refinement_round2b_integrity_{slug}.json").read_text())
    d_mf1_C = round(C["macro_f1"] - A["macro_f1"], 4)
    row = {
        "model": name,
        "A_control": A, "B_full_rubric": B, "C_refined": C,
        "C_integrity": itC["verdict"], "C_schema": itC["schema_parse_success"], "C_job_norm": itC["job_normalization_success"], "C_retries": itC["total_retries"],
        "delta_macro_f1_C_vs_A": d_mf1_C,
        "delta_macro_f1_C_vs_B": round(C["macro_f1"] - B["macro_f1"], 4),
        "delta_ecc_C_vs_A": round(C["ecc"] - A["ecc"], 4),
        "delta_accuracy_C_vs_A": round(C["accuracy"] - A["accuracy"], 4),
        "hypothesis_support_C_vs_A": support(d_mf1_C),
        "delta_strong_r": round(C["strong"][1] - A["strong"][1], 4),
        "delta_strong_p": round(C["strong"][0] - A["strong"][0], 4),
        "delta_partial_p": round(C["partial"][0] - A["partial"][0], 4),
        "delta_partial_r": round(C["partial"][1] - A["partial"][1], 4),
        "delta_missing_r": round(C["missing"][1] - A["missing"][1], 4),
        "C_partial_precision": C["partial"][0],
        "partial_precision_ge_060": (C["partial"][0] is not None and C["partial"][0] >= 0.60),
        "delta_S_to_P": (C["S_to_P"] - A["S_to_P"]) if (C["S_to_P"] is not None and A["S_to_P"] is not None) else None,
        "delta_M_to_P": (C["M_to_P"] - A["M_to_P"]) if (C["M_to_P"] is not None and A["M_to_P"] is not None) else None,
        "delta_chinese_jd_mf1": round((C["chinese_jd_mf1"] or 0) - (A["chinese_jd_mf1"] or 0), 4),
        "delta_score_vs_hmf": round((C["score_vs_hmf"] or 0) - (A["score_vs_hmf"] or 0), 4),
        "delta_total_tokens_C_vs_A": (C["total_tokens"] - (108549 if name == "qwen3.8-max" else 107576)),
        "coverage_full_C": C["coverage"] == "100/100" and C["job_norm"] == "30/30",
        "grounding_preserved_C": (C["grounding"] == 1.0 and C["unsupported"] == 0.0),
    }
    out["models_detail"].append(row)

# decision rules
def kimi_decision(row):
    C = row["C_refined"]
    cond = (C["coverage"] == "100/100" and C["ecc"] is not None and C["ecc"] >= 0.74
            and C["macro_f1"] is not None and C["macro_f1"] >= 0.740 and C["grounding"] == 1.0 and C["unsupported"] == 0.0)
    return ("job-fit-v3-rubric-refined-v2" if cond else "job-fit-v3-matchable-only",
            cond, "coverage=100/100 AND ECC>=0.74 AND MacroF1>=0.740 AND grounding not degraded")


def qwen_decision(row):
    C = row["C_refined"]
    meaningful = (C["macro_f1"] - row["A_control"]["macro_f1"]) >= 0.02
    cond = (C["coverage"] == "100/100" and C["ecc"] is not None and C["ecc"] >= 0.71
            and meaningful and C["grounding"] == 1.0 and C["unsupported"] == 0.0)
    return ("job-fit-v3-rubric-refined-v2" if cond else "job-fit-v3-matchable-only",
            cond, "coverage=100/100 AND ECC>=0.71 AND MacroF1 improves meaningfully AND grounding not degraded")


for row in out["models_detail"]:
    if row["model"] == "kimi-k3":
        pid, met, rule = kimi_decision(row)
        row["decision_rule"] = rule
        row["decision_met"] = met
        row["final_v1_prompt"] = pid
    else:
        pid, met, rule = qwen_decision(row)
        row["decision_rule"] = rule
        row["decision_met"] = met
        row["final_v1_prompt"] = pid

(R2B / "prompt_refinement_round2b_metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

print(json.dumps([{"model": r["model"], "A_mf1": r["A_control"]["macro_f1"], "B_mf1": r["B_full_rubric"]["macro_f1"], "C_mf1": r["C_refined"]["macro_f1"],
                   "dMF1_CvsA": r["delta_macro_f1_C_vs_A"], "support": r["hypothesis_support_C_vs_A"],
                   "A_ecc": r["A_control"]["ecc"], "C_ecc": r["C_refined"]["ecc"], "C_coverage": r["C_refined"]["coverage"],
                   "C_partial_p": r["C_partial_precision"], "partial_p_ge_060": r["partial_precision_ge_060"],
                   "dS->P": r["delta_S_to_P"], "dM->P": r["delta_M_to_P"], "C_grounding": r["C_refined"]["grounding"],
                   "d_chinese_jd": r["delta_chinese_jd_mf1"], "d_hmf": r["delta_score_vs_hmf"],
                   "d_tokens_CvsA": r["delta_total_tokens_C_vs_A"], "integrity": r["C_integrity"],
                   "decision_met": r["decision_met"], "final_v1_prompt": r["final_v1_prompt"]} for r in out["models_detail"]], ensure_ascii=False, indent=1))
print("wrote prompt_refinement_round2b_metrics.json")
