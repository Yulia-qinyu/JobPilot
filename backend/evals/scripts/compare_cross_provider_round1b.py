"""Aggregate Round 1B cross-provider results into comparison / Pareto / shortlist artifacts.

Usage:  python backend/evals/scripts/compare_cross_provider_round1b.py

Reads cross_provider_round1b_metrics_<slug>.json for the four new candidates and the FROZEN
reference values for claude-sonnet-4-5-20250929 (Baseline V1 — NOT rerun). Writes:
  cross_provider_round1b_metrics.json / .csv
  cross_provider_round1b_comparison.md
  cross_provider_round1b_pareto.md
  cross_provider_round1b_shortlist.md
No inference. No Ground Truth mutation. No production change.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

OUT = Path("/Users/yulia/Documents/JobPilot/backend/evals/benchmark_cross_provider")

# Frozen — SONNET_PRODUCTION_BASELINE = Baseline V1. NEVER modified/merged. Kept separately as the
# current-production-system reference. NOT the apples-to-apples Round 1B model control.
SONNET = {
    "provider": "anthropic", "model": "claude-sonnet-4-5-20250929 (PRODUCTION_BASELINE)",
    "role": "SONNET_PRODUCTION_BASELINE",
    "source": "Baseline V1 (job_match_baseline_claude_current_v1) — FULL 7-field production schema", "model_calls": 0,
    "reconciliation": {"expected": 100, "reconciled": 91, "unreconciled": 9},
    "classification": {"accuracy": 0.6813, "macro": {"precision": None, "recall": None, "f1": 0.6919},
                       "per_class": {
                           "Strong": {"precision": 0.879, "recall": 0.630, "f1": 0.734},
                           "Partial": {"precision": 0.477, "recall": 0.778, "f1": 0.591},
                           "Missing": {"precision": 0.857, "recall": 0.667, "f1": 0.750}}},
    "directional_errors": {"Strong->Partial": 17, "Missing->Partial": 6},
    "system": {"raw_schema_parse_success": "30/30", "job_normalization_success": "29/30",
               "requirement_prediction_coverage": "91/100", "effective_correct_coverage": 0.620},
    "grounding": {"grounding_rate": 1.000, "unsupported_match_rate": 0.000},
    "match_score": {"mae_vs_gt_score": 13.45, "spearman_model_vs_gt_score": 0.707,
                    "spearman_model_vs_human_match_fit": 0.537,
                    "reference_gt_score_vs_human_match_fit_spearman": 0.845},
    "latency": {"mean_ms": 21068, "p90_ms": 30584},
    "tokens": {"input": 127696, "output": 31365, "reasoning": 0, "total": 159061},
    "cost": {"cost_status": "VERIFIED", "rate_input_per_mtok_usd": 3.0, "rate_output_per_mtok_usd": 15.0,
             "total_usd": round(127696 / 1e6 * 3.0 + 31365 / 1e6 * 15.0, 4)},
    "flags": "reference; standard single-pass; temperature=0; FULL 7-field production schema",
}

SLUGS = [
    ("sonnet-comparable", "claude-sonnet-4-5-20250929 (COMPARABLE_CONTROL)", "SONNET_ROUND1B_COMPARABLE_CONTROL"),
    ("qwen-qwen3.8-max", "qwen3.8-max", "QWEN_HIGH_CAPABILITY"),
    ("qwen-qwen3.8-flash", "qwen3.8-flash", "QWEN_COST_QUALITY"),
    ("deepseek-v4-pro", "deepseek-v4-pro", "DEEPSEEK_HIGH_VALUE"),
    ("moonshot-kimi-k3", "kimi-k3", "KIMI_CHINESE_HIGH_CAPABILITY"),
]

models = {"claude-sonnet-4-5-20250929 (PRODUCTION_BASELINE)": SONNET}
for slug, mid, role in SLUGS:
    p = OUT / f"cross_provider_round1b_metrics_{slug}.json"
    if not p.exists():
        print(f"WARNING missing {p.name}")
        continue
    m = json.loads(p.read_text())
    m["role"] = role
    m["flags"] = "; ".join(filter(None, [
        f"reasoning={m['experiment_contract']['reasoning_mode']}",
        "reasoning_comparability_flag" if m['experiment_contract']['reasoning_comparability_flag'] else "",
        "temperature_comparability_flag(temp=1)" if m['experiment_contract']['temperature_comparability_flag'] else f"temp={m['experiment_contract']['temperature']}",
        "4-field Section D + TRANSPORT_NORMALIZATION_MAPPING",
    ]))
    models[mid] = m

ORDER = ["claude-sonnet-4-5-20250929 (COMPARABLE_CONTROL)", "qwen3.8-max", "qwen3.8-flash",
         "deepseek-v4-pro", "kimi-k3", "claude-sonnet-4-5-20250929 (PRODUCTION_BASELINE)"]
ORDER = [x for x in ORDER if x in models]


def g(m, *path, default=None):
    cur = m
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def slice_acc(m, name):
    s = g(m, "slice_metrics", name)
    if not s:
        return None
    return {"n_reconciled": s.get("n_reconciled"), "accuracy": s.get("accuracy"),
            "macro_f1": s.get("macro_f1"), "errors": s.get("errors"),
            "directional": s.get("directional")}


# Deltas/bands are now computed vs the SONNET_ROUND1B_COMPARABLE_CONTROL (same Section A + Section D
# contract) when it is available — the apples-to-apples reference. Falls back to the production
# baseline 0.692 only if the comparable control has not been run yet.
_CTRL_KEY = "claude-sonnet-4-5-20250929 (COMPARABLE_CONTROL)"
SONNET_MACRO_F1 = (g(models[_CTRL_KEY], "classification", "macro", "f1")
                   if _CTRL_KEY in models else 0.692)
SONNET_DELTA_BASIS = ("SONNET_ROUND1B_COMPARABLE_CONTROL" if _CTRL_KEY in models
                      else "SONNET_PRODUCTION_BASELINE (0.692) — comparable control not yet run")
_NO_DELTA = {_CTRL_KEY, "claude-sonnet-4-5-20250929 (PRODUCTION_BASELINE)"}


def band(delta):
    if delta is None:
        return "n/a"
    if delta < 0:
        return f"REGRESSION ({delta:+.3f})"
    if delta < 0.02:
        return f"not compelling ({delta:+.3f})"
    if delta < 0.05:
        return f"small ({delta:+.3f})"
    if delta < 0.10:
        return f"meaningful ({delta:+.3f})"
    return f"large ({delta:+.3f})"


rows = []
for mid in ORDER:
    m = models[mid]
    mf1 = g(m, "classification", "macro", "f1")
    rows.append({
        "model": mid, "role": m.get("role", "REFERENCE"),
        "macro_f1": mf1,
        "delta_vs_sonnet_ctrl": (round(mf1 - SONNET_MACRO_F1, 4) if (mf1 is not None and SONNET_MACRO_F1 is not None) else None),
        "band": band(round(mf1 - SONNET_MACRO_F1, 4) if (mf1 is not None and SONNET_MACRO_F1 is not None and mid not in _NO_DELTA) else None),
        "ecc": g(m, "system", "effective_correct_coverage"),
        "accuracy": g(m, "classification", "accuracy"),
        "strong_p": g(m, "classification", "per_class", "Strong", "precision"),
        "strong_r": g(m, "classification", "per_class", "Strong", "recall"),
        "strong_f1": g(m, "classification", "per_class", "Strong", "f1"),
        "partial_p": g(m, "classification", "per_class", "Partial", "precision"),
        "partial_r": g(m, "classification", "per_class", "Partial", "recall"),
        "partial_f1": g(m, "classification", "per_class", "Partial", "f1"),
        "missing_p": g(m, "classification", "per_class", "Missing", "precision"),
        "missing_r": g(m, "classification", "per_class", "Missing", "recall"),
        "missing_f1": g(m, "classification", "per_class", "Missing", "f1"),
        "strong_to_partial": g(m, "directional_errors", "Strong->Partial"),
        "missing_to_partial": g(m, "directional_errors", "Missing->Partial"),
        "or_list": slice_acc(m, "or_list"),
        "technology_adjacency": slice_acc(m, "technology_adjacency"),
        "project_based_evidence": slice_acc(m, "project_based_evidence"),
        "chinese_jd_macro_f1": g(m, "slice_metrics", "chinese_jd", "macro_f1"),
        "chinese_jd_accuracy": g(m, "slice_metrics", "chinese_jd", "accuracy"),
        "grounding_rate": g(m, "grounding", "grounding_rate"),
        "unsupported_match_rate": g(m, "grounding", "unsupported_match_rate"),
        "job_normalization": g(m, "system", "job_normalization_success"),
        "requirement_coverage": g(m, "system", "requirement_prediction_coverage"),
        "reconciled": g(m, "reconciliation", "reconciled"),
        "match_score_mae": g(m, "match_score", "mae_vs_gt_score"),
        "score_vs_gt_spearman": g(m, "match_score", "spearman_model_vs_gt_score"),
        "score_vs_hmf_spearman": g(m, "match_score", "spearman_model_vs_human_match_fit"),
        "mean_latency_ms": g(m, "latency", "mean_ms"),
        "p90_latency_ms": g(m, "latency", "p90_ms"),
        "input_tokens": g(m, "tokens", "input"),
        "output_tokens": g(m, "tokens", "output"),
        "reasoning_tokens": g(m, "tokens", "reasoning"),
        "total_tokens": g(m, "tokens", "total"),
        "cost_status": g(m, "cost", "cost_status"),
        "cost_total_usd": g(m, "cost", "total_usd"),
        "flags": m.get("flags", ""),
        "adjacency_fp": g(m, "adjacency_false_positives_gt_missing_to_partial_or_strong"),
        "project_over_credited": g(m, "project_over_credited"),
        "project_under_credited": g(m, "project_under_credited"),
        "total_retries": g(m, "total_retries", default=0),
        "integrity": "INTEGRITY_OK" if mid == "claude-sonnet-4-5-20250929" else None,
    })

for slug, mid, role in SLUGS:
    ipath = OUT / f"cross_provider_round1b_integrity_{slug}.json"
    if ipath.exists():
        v = json.loads(ipath.read_text()).get("verdict")
        for r in rows:
            if r["model"] == mid:
                r["integrity"] = v

agg = {
    "benchmark": "round1b-cross-provider-screening",
    "dataset": "job_match_eval_dataset_v1",
    "dataset_governance": "DEVELOPMENT / MODEL-SELECTION benchmark — NOT a final unbiased held-out test. "
                          "Ground Truth was inspected, baseline errors analysed, and failure slices derived "
                          "from observed errors before this comparison. Any Round 1B gain is development-set "
                          "performance. Dataset V2 remains the held-out validation/test set.",
    "ground_truth": "job-match-ground-truth-v2 (sha 52cda176...)",
    "two_sonnet_records": {
        "SONNET_PRODUCTION_BASELINE": "Baseline V1 (job_match_baseline_claude_current_v1). FULL 7-field production "
                                      "schema. NOT rerun, NOT modified, NEVER merged. Purpose: current production-system state.",
        "SONNET_ROUND1B_COMPARABLE_CONTROL": "New 30-call run under the SAME Round 1B Section A + Section D 4-field "
                                             "contract + TRANSPORT_NORMALIZATION_MAPPING as the new candidates. Anthropic "
                                             "messages.parse binding the lean Section-D schema; temperature=0; max_tokens=4096; "
                                             "no thinking param. Purpose: apples-to-apples model comparison.",
    },
    "sonnet_delta_basis": SONNET_DELTA_BASIS,
    "section_d": "canonical 4-field output contract (transport-validated). ALL Round 1B model rows — including the "
                 "SONNET_ROUND1B_COMPARABLE_CONTROL — faced this leaner contract. The SONNET_PRODUCTION_BASELINE row "
                 "used the FULL 7-field production schema and is shown separately for product-current-state reference.",
    "transport_normalization_mapping": "match_label->match_status, evidence_ids->evidence_source_ids, reason->reason; "
                                       "importance := frozen canonical requirement importance; is_hard_requirement := False "
                                       "(v2_matchable); confidence := Medium constant. Non-semantic; identical for every "
                                       "Round 1B model row incl. the Sonnet comparable control.",
    "quality_gates": {"macro_f1_min": 0.75, "ecc_min": 0.75, "grounding_min": 0.98, "unsupported_max": 0.02,
                      "strong_recall_min": 0.75, "strong_precision_min": 0.80, "partial_precision_min": 0.60,
                      "missing_recall_min": 0.667},
    "improvement_bands_vs_sonnet_comparable_control": {"lt_0.02": "not compelling", "0.02_0.05": "small",
                                                       "0.05_0.10": "meaningful", "ge_0.10": "large", "negative": "regression"},
    "models": rows,
}
(OUT / "cross_provider_round1b_metrics.json").write_text(json.dumps(agg, ensure_ascii=False, indent=1))

# CSV
cols = ["model", "role", "macro_f1", "delta_vs_sonnet_ctrl", "band", "ecc", "accuracy",
        "strong_p", "strong_r", "strong_f1", "partial_p", "partial_r", "partial_f1",
        "missing_p", "missing_r", "missing_f1", "strong_to_partial", "missing_to_partial",
        "chinese_jd_macro_f1", "chinese_jd_accuracy", "grounding_rate", "unsupported_match_rate",
        "job_normalization", "requirement_coverage", "reconciled", "match_score_mae",
        "score_vs_gt_spearman", "score_vs_hmf_spearman", "mean_latency_ms", "p90_latency_ms",
        "input_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "cost_status",
        "cost_total_usd", "adjacency_fp", "project_over_credited", "total_retries", "integrity", "flags"]
import csv as _csv
with (OUT / "cross_provider_round1b_metrics.csv").open("w", newline="") as fh:
    w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(json.dumps({"models": [{"model": r["model"], "macro_f1": r["macro_f1"], "band": r["band"],
                              "ecc": r["ecc"], "chinese_jd_macro_f1": r["chinese_jd_macro_f1"],
                              "grounding": r["grounding_rate"], "mean_latency_ms": r["mean_latency_ms"],
                              "total_tokens": r["total_tokens"], "integrity": r["integrity"]} for r in rows]},
                 ensure_ascii=False, indent=1))
print("wrote cross_provider_round1b_metrics.json / .csv")
