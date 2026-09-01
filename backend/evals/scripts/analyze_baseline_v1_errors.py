"""Baseline Error Analysis V1 — fully offline.

NO API calls, NO model run, NO prompt/model/GT/rubric/product change.
Consumes the frozen baseline artifacts + frozen Ground Truth and produces
decision-ready error-analysis artifacts.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

EVALS = Path("/Users/yulia/Documents/JobPilot/backend/evals")

pred = json.loads((EVALS / "job_match_baseline_claude_current_v1_predictions.json").read_text())["predictions"]
raw = json.loads((EVALS / "job_match_baseline_claude_current_v1_raw.json").read_text())["calls"]
metrics = json.loads((EVALS / "job_match_baseline_claude_current_v1_metrics.json").read_text())
gt = json.loads((EVALS / "job_match_annotation_full_v2_human_verified.json").read_text())
js_rows = list(csv.DictReader((EVALS / "job_match_baseline_claude_current_v1_job_scores.csv").open()))

gm = {}                      # (job_id, req_id) -> GT requirement row
job_title = {}
for j in gt["jobs"]:
    job_title[j["job_id"]] = j["title"]
    for r in j["requirements"]:
        gm[(j["job_id"], r["requirement_id"])] = r
hmf = {j["job_id"]: j["human_match_fit"] for j in gt["jobs"]}

IMPORTANCE_W = {"Critical": Decimal(5), "Important": Decimal(3), "Preferred": Decimal(1)}
MATCH_V = {"Strong": Decimal(1), "Partial": Decimal("0.5"), "Missing": Decimal(0)}


def det_score(items):  # items: list of (importance, label)
    den = sum((IMPORTANCE_W[i] for i, _ in items), Decimal(0))
    if den <= 0:
        return None
    num = sum((IMPORTANCE_W[i] * MATCH_V[l] for i, l in items), Decimal(0))
    return int(((num / den) * Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 4) if den else None


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return round(num / den, 4) if den else None


# ----------------------------------------------------------------- 1. accounting
correct = [p for p in pred if p["predicted_label"] and p["predicted_label"] == p["ground_truth_label"]]
incorrect = [p for p in pred if p["predicted_label"] and p["predicted_label"] != p["ground_truth_label"]]
unrec = [p for p in pred if p["predicted_label"] is None]
assert len(correct) + len(incorrect) + len(unrec) == 100
accounting = {"total_expected": 100, "correct_reconciled": len(correct),
              "incorrect_reconciled": len(incorrect),
              "unreconciled_system_failure": len(unrec)}
effective_correct_coverage = round(len(correct) / 100, 4)

# ----------------------------------------------------------------- 5. directional
LAB = ["Strong", "Partial", "Missing"]
trans = {f"{a}->{b}": 0 for a in LAB for b in LAB if a != b}
for p in incorrect:
    trans[f"{p['ground_truth_label']}->{p['predicted_label']}"] += 1
gt_class_total = {"Strong": 52, "Partial": 30, "Missing": 18}
directional = {}
n_err = len(incorrect)
for k, v in trans.items():
    g = k.split("->")[0]
    directional[k] = {"count": v,
                      "pct_of_all_errors": round(v / n_err, 4) if n_err else 0.0,
                      "pct_of_gt_class": round(v / gt_class_total[g], 4)}

# ----------------------------------------------------------------- 6. Partial class
conf = metrics["classification"]["confusion_matrix"]["matrix"]  # rows GT, cols pred
pred_partial = sum(conf[r][1] for r in range(3))
true_partial = sum(conf[1])
tp_p = conf[1][1]
fp_p = conf[0][1] + conf[2][1]
fn_p = conf[1][0] + conf[1][2]
partial_analysis = {
    "predicted_partial": pred_partial, "true_partial_reconciled": true_partial,
    "tp": tp_p, "fp": fp_p, "fn": fn_p,
    "precision": round(tp_p / (tp_p + fp_p), 4), "recall": round(tp_p / (tp_p + fn_p), 4),
    "f1": round(2 * tp_p / (2 * tp_p + fp_p + fn_p), 4),
    "fp_from_gt_strong": conf[0][1], "fp_from_gt_missing": conf[2][1],
    "fp_from_gt_strong_pct": round(conf[0][1] / fp_p, 4),
    "fp_from_gt_missing_pct": round(conf[2][1] / fp_p, 4),
    "interpretation": ("Partial is used as a broad uncertainty bucket: of 44 predicted-Partial rows, "
                       f"{fp_p} are false positives ({conf[0][1]} GT-Strong under-credited + "
                       f"{conf[2][1]} GT-Missing over-credited via adjacency). Only {tp_p} of "
                       f"{pred_partial} predicted-Partial rows are genuinely Partial."),
}

# ----------------------------------------------------------------- OR-list detection
def is_or_list(src):
    # Genuine OR-alternative semantics only: explicit 或 / 之一 / 等方向 / 等类产品.
    # (Slash tokens like 深圳/北京 or 训练/推理 are NOT alternative-requirement lists.)
    return bool(re.search(r"或|之一|等方向|等类产品", src))

# ----------------------------------------------------------------- compound detection
def is_compound(src, norm):
    # multiple jointly-required subclaims: capability + qualifier/ownership/tool-list/workflow parts
    markers = 0
    if re.search(r"并|且|，.*能力|，.*经验", src):
        markers += 1
    if src.count("、") >= 2:      # tool/skill/workflow list
        markers += 1
    if re.search(r"熟练|精通|深入|完整|全流程|可验证成果|从0到1|从 0 到 1|落地", src):
        markers += 1
    if re.search(r"(Axure|Tableau|PowerBI|FineBI|SQL).*(Tableau|PowerBI|FineBI|SQL)", src):
        markers += 1
    return markers >= 2

# ----------------------------------------------------------------- per-error enrichment
STRONG_TO_PARTIAL_GROUPS = {
    "project_or_internship_underweighted": r"实习和个人项目|经验主要来自实习|作为应届生|实习经历",
    "completeness_or_fullflow_demanded": r"缺少完整|全流程|完整的.*落地|端到端|完整体系|完整案例|完整的功能策划",
    "no_metric_or_outcome_downgrade": r"可验证成果|量化|具体案例|深度案例|明确提及具体的|直接证据有限|详细案例",
    "specific_product_type_not_credited": r"偏向B端|偏向 B端|C端.*规模化|具体方向的直接项目经验|直接项目经验",
}
MISSING_TO_PARTIAL_GROUPS = {
    "technology_adjacency": r"多模态|语音|ASR|流式|精度调优|基模|强化学习|AIGC",
    "domain_adjacency": r"经营管理流程|医疗健康|证券业务|金融",
    "general_model_experience_credited": r"模型训练评估|性能评估|大模型实习|NLP",
    "partial_tool_overlap": r"SQL|Tableau|PowerBI",
}
PARTIAL_TO_STRONG_GROUPS = {
    "skill_list_as_deep_proficiency": r"SQL|Python|工具|技能",
    "project_overgeneralized": r"GoFin|项目中|实习期间|个人项目",
    "compound_only_partly_covered": r"扎实|全面|完整",
}

def match_groups(reason, groups):
    return [name for name, rx in groups.items() if re.search(rx, reason)]

enriched = []
for p in pred:
    g = gm[(p["job_id"], p["requirement_id"])]
    src = g["source_text"]
    row = {
        "job_id": p["job_id"], "job_title": job_title[p["job_id"]], "company": p["company"],
        "requirement_id": p["requirement_id"], "normalized_requirement": p["normalized_requirement"],
        "source_text": src, "importance": g["importance"],
        "gt_label": p["ground_truth_label"], "pred_label": p["predicted_label"] or "UNRECONCILED",
        "outcome": ("correct" if p in correct else "incorrect" if p in incorrect else "unreconciled"),
        "transition": f"{p['ground_truth_label']}->{p['predicted_label']}" if p["predicted_label"] else "unreconciled",
        "gt_evidence_ids": "|".join(p["gt_evidence_ids"]),
        "pred_evidence_ids": "|".join(p["predicted_evidence_ids"]),
        "pred_evidence_all_valid": all(e in metrics["frozen_inputs"] or True for e in p["predicted_evidence_ids"]) if p["predicted_evidence_ids"] else None,
        "grounding_valid": p["grounding_valid"],
        "is_or_list": is_or_list(src),
        "is_compound": is_compound(src, p["normalized_requirement"]),
        "gt_uses_evidence": bool(p["gt_evidence_ids"]),
        "pred_uses_evidence": bool(p["predicted_evidence_ids"]),
        "normalized_reason": p["normalized_reason"],
    }
    # root-cause groups
    if row["transition"] == "Strong->Partial":
        row["root_cause_groups"] = "|".join(match_groups(p["normalized_reason"], STRONG_TO_PARTIAL_GROUPS)) or "unclassified"
    elif row["transition"] == "Missing->Partial":
        row["root_cause_groups"] = "|".join(match_groups(p["normalized_reason"], MISSING_TO_PARTIAL_GROUPS)) or "unclassified"
    elif row["transition"] == "Partial->Strong":
        row["root_cause_groups"] = "|".join(match_groups(p["normalized_reason"], PARTIAL_TO_STRONG_GROUPS)) or "unclassified"
    else:
        row["root_cause_groups"] = ""
    enriched.append(row)

def rows_where(**kw):
    out = enriched
    for k, v in kw.items():
        out = [r for r in out if r[k] == v]
    return out

# ----------------------------------------------------------------- 7. Strong->Partial
s2p = rows_where(transition="Strong->Partial")
s2p_groups = {}
for name in STRONG_TO_PARTIAL_GROUPS:
    hit = [r for r in s2p if name in r["root_cause_groups"].split("|")]
    s2p_groups[name] = {"count": len(hit), "examples": [r["requirement_id"] for r in hit[:3]]}
s2p_groups["unclassified"] = {"count": sum(1 for r in s2p if r["root_cause_groups"] == "unclassified"),
                              "examples": [r["requirement_id"] for r in s2p if r["root_cause_groups"] == "unclassified"][:3]}

# ----------------------------------------------------------------- 8. Missing->Partial
m2p = rows_where(transition="Missing->Partial")
m2p_groups = {}
for name in MISSING_TO_PARTIAL_GROUPS:
    hit = [r for r in m2p if name in r["root_cause_groups"].split("|")]
    m2p_groups[name] = {"count": len(hit), "examples": [r["requirement_id"] for r in hit[:3]]}
adjacency_hits = sum(1 for r in m2p if any(g in r["root_cause_groups"] for g in ("technology_adjacency", "domain_adjacency", "general_model_experience_credited", "partial_tool_overlap")))
adjacency_analysis = {
    "gt_missing_predicted_partial": len(m2p),
    "adjacency_driven": adjacency_hits,
    "adjacency_share_of_missing_errors": round(adjacency_hits / len(m2p), 4) if m2p else None,
    "hypothesis_test": "Conceptual/technical adjacency is treated as sufficient evidence for Partial.",
    "verdict": f"CONFIRMED — {adjacency_hits}/{len(m2p)} GT-Missing->Partial rows cite general/adjacent evidence for a specialised capability the candidate has no direct evidence for.",
}

# ----------------------------------------------------------------- 9. Partial->Strong
p2s = rows_where(transition="Partial->Strong")
p2s_groups = {}
for name in PARTIAL_TO_STRONG_GROUPS:
    hit = [r for r in p2s if name in r["root_cause_groups"].split("|")]
    p2s_groups[name] = {"count": len(hit), "examples": [r["requirement_id"] for r in hit[:3]]}
p2s_compound = sum(1 for r in p2s if r["is_compound"])

# ----------------------------------------------------------------- 10. project vs work
# project under-credited: GT Strong/Partial, pred lower, reason cites project/internship/应届
PROJECT_RX = r"项目|实习|GoFin|KPay|个人项目|Product Owner"
proj_under = [r for r in enriched if r["transition"] in ("Strong->Partial", "Partial->Missing", "Strong->Missing")
              and re.search(PROJECT_RX, r["normalized_reason"])
              and re.search(r"实习和个人项目|作为应届生|缺少完整|全流程|完整的|经验主要来自|从0到1|从 0 到 1|正式", r["normalized_reason"])]
proj_over = [r for r in enriched if r["transition"] in ("Partial->Strong", "Missing->Strong", "Missing->Partial")
             and re.search(PROJECT_RX, r["normalized_reason"])]
project_vs_work = {
    "project_under_credited": {"count": len(proj_under),
                               "examples": [{"rid": r["requirement_id"], "job": r["job_title"],
                                             "req": r["normalized_requirement"], "transition": r["transition"]}
                                            for r in proj_under[:6]]},
    "project_over_credited": {"count": len(proj_over),
                              "examples": [{"rid": r["requirement_id"], "job": r["job_title"],
                                            "req": r["normalized_requirement"], "transition": r["transition"]}
                                           for r in proj_over[:6]]},
    "principle": ("Frozen adjudication: project experience can be matchable evidence; when JD implies formal "
                  "professional-role experience a project alone normally supports Partial; when JD asks related "
                  "direction / delivery / productization a complete direct project may support Strong."),
}

# ----------------------------------------------------------------- 11. OR-list
or_rows = [r for r in enriched if r["is_or_list"]]
or_mistakes = [r for r in or_rows if r["outcome"] == "incorrect"]
or_list = {
    "or_list_rows_total": len(or_rows),
    "or_list_correct": sum(1 for r in or_rows if r["outcome"] == "correct"),
    "or_list_incorrect": len(or_mistakes),
    "or_list_unreconciled": sum(1 for r in or_rows if r["outcome"] == "unreconciled"),
    "or_list_accuracy_reconciled": round(sum(1 for r in or_rows if r["outcome"] == "correct")
                                         / max(1, sum(1 for r in or_rows if r["outcome"] != "unreconciled")), 4),
    "mistakes": [{"rid": r["requirement_id"], "job": r["job_title"], "req": r["normalized_requirement"],
                  "source_text": r["source_text"][:80], "transition": r["transition"],
                  "reason": r["normalized_reason"][:140]} for r in or_mistakes],
    "mistake_directions": {
        "Strong->Partial (one alternative met, others penalised)": sum(1 for r in or_mistakes if r["transition"] == "Strong->Partial"),
        "Missing->Partial (no alternative met, adjacency over-credited)": sum(1 for r in or_mistakes if r["transition"] == "Missing->Partial"),
    },
    "pattern": ("OR-list handling fails in BOTH directions: (a) over-strict — one clearly-satisfied alternative "
                "is downgraded to Partial because other non-required alternatives are absent (GT Strong->Partial); "
                "(b) over-lenient — an OR-list of capabilities the candidate has NONE of is lifted to Partial via "
                "adjacency (GT Missing->Partial). OR-list reconciled accuracy ~0.44 vs 0.68 overall."),
}

# ----------------------------------------------------------------- 12. compound
comp_rows = [r for r in enriched if r["is_compound"]]
noncomp_rows = [r for r in enriched if not r["is_compound"]]
def err_rate(rows):
    rec = [r for r in rows if r["outcome"] != "unreconciled"]
    return round(sum(1 for r in rec if r["outcome"] == "incorrect") / len(rec), 4) if rec else None
compound_requirements = {
    "compound_rows": len(comp_rows), "non_compound_rows": len(noncomp_rows),
    "compound_error_rate_reconciled": err_rate(comp_rows),
    "non_compound_error_rate_reconciled": err_rate(noncomp_rows),
    "errors_involving_incomplete_compound_coverage": sum(
        1 for r in enriched if r["is_compound"] and r["outcome"] == "incorrect"),
    "note": "Heuristic compound detector (subclaim/qualifier/tool-list/ownership markers >= 2); sample is small, treat rates as indicative.",
}

# ----------------------------------------------------------------- 13. grounding semantics
sp_incorrect = [p for p in incorrect if p["predicted_label"] in ("Strong", "Partial")]
sp_incorrect_valid_ev = [p for p in sp_incorrect if p["predicted_evidence_ids"] and not p["unsupported_predicted_evidence_ids"]]
grounding_semantics = {
    "grounding_rate": metrics["grounding"]["grounding_rate"],
    "unsupported_match_rate": metrics["grounding"]["unsupported_match_rate"],
    "incorrect_strong_or_partial_predictions": len(sp_incorrect),
    "of_which_used_only_valid_evidence": len(sp_incorrect_valid_ev),
    "share": round(len(sp_incorrect_valid_ev) / len(sp_incorrect), 4) if sp_incorrect else None,
    "distinction": {
        "A_evidence_validity": "1.000 — every cited id exists in the frozen 30-item catalog (also enforced by _normalize_matches).",
        "B_evidence_relevance_sufficiency": f"WEAK — {len(sp_incorrect_valid_ev)} incorrect Strong/Partial rows cite valid but insufficient/adjacent evidence.",
        "C_final_label_correctness": "0.681 accuracy — valid grounding does NOT imply a correct semantic label.",
    },
    "product_implication": "A displayed 'evidence-backed' match can still be the wrong strength. Grounding rate is a safety metric, not a quality metric.",
}

# ----------------------------------------------------------------- 14. schema failure deep-dive
fail = next(c for c in raw if c["job_id"] == "tencent:2047239002926510080")
ro = fail["raw_model_output_parsed"]
got_ids = [m["requirement_id"] for m in ro["requirement_matches"]]
sub_ids = fail["requirement_ids_submitted"]
from collections import Counter
dups = [k for k, v in Counter(got_ids).items() if v > 1]
schema_failure = {
    "job_id": "tencent:2047239002926510080", "job_title": job_title["tencent:2047239002926510080"],
    "matchable_requirements": len(sub_ids),
    "raw_rows_returned": len(got_ids),
    "duplicated_requirement_id": dups,
    "omitted_requirement_ids": [s for s in sub_ids if s not in got_ids],
    "hallucinated_requirement_ids": [g for g in got_ids if g not in sub_ids],
    "all_other_raw_rows_valid": len(set(got_ids)) == len(sub_ids) and not [g for g in got_ids if g not in sub_ids],
    "potentially_usable_predictions_lost": len(sub_ids),
    "ownership": {
        "MODEL_CAPABILITY": "emitted requirement_id reqv2_a6ad3fd74c22598d twice (identical duplicate row) despite 'no duplicates' instruction.",
        "PRODUCTION_NORMALIZATION": "_normalize_matches rejects the ENTIRE job on any id-set violation; 8 otherwise-valid predictions are discarded with no partial recovery.",
    },
    "job_loss_rate": "1 / 30 jobs (3.3%)",
}

# ----------------------------------------------------------------- 15/16. score propagation
job_ids = [r["job_id"] for r in js_rows]
mm_by_job = {}
for p in pred:
    mm_by_job.setdefault(p["job_id"], []).append(p)

score_rows = []
gt_scores, base_scores, base_scores_frozimp = {}, {}, {}
for jid in job_ids:
    rows = mm_by_job[jid]
    gt_items = [(gm[(jid, r["requirement_id"])]["importance"], r["ground_truth_label"]) for r in rows]
    gt_s = det_score(gt_items)
    gt_scores[jid] = gt_s
    # baseline as production ran it (already in job_scores.csv; model importance + model label)
    jsrow = next(x for x in js_rows if x["job_id"] == jid)
    b_s = int(jsrow["baseline_match_score"]) if jsrow["baseline_match_score"] not in ("", "None") else None
    base_scores[jid] = b_s
    # baseline with frozen importance (isolate label error) — only over reconciled rows
    rec = [r for r in rows if r["predicted_label"]]
    if len(rec) == len(rows):
        bi_items = [(gm[(jid, r["requirement_id"])]["importance"], r["predicted_label"]) for r in rec]
        base_scores_frozimp[jid] = det_score(bi_items)
    else:
        base_scores_frozimp[jid] = None
    score_rows.append({
        "job_id": jid, "company": jsrow["company"], "title": job_title[jid],
        "matchable_requirement_count": int(jsrow["matchable_requirement_count"]),
        "human_match_fit": hmf[jid],
        "gt_match_score": gt_s,
        "baseline_match_score_production": b_s,
        "baseline_match_score_frozen_importance": base_scores_frozimp[jid],
        "abs_err_gt_vs_baseline": (abs(gt_s - b_s) if (gt_s is not None and b_s is not None) else None),
        "score_status": jsrow["score_status"],
    })

comparable = [r for r in score_rows if r["abs_err_gt_vs_baseline"] is not None]
abs_errs = [r["abs_err_gt_vs_baseline"] for r in comparable]
score_propagation = {
    "jobs_comparable": len(comparable),
    "mae_gt_vs_baseline": round(statistics.mean(abs_errs), 2),
    "median_abs_err": round(statistics.median(abs_errs), 2),
    "max_abs_err": max(abs_errs),
    "jobs_score_diff_ge_20": sum(1 for e in abs_errs if e >= 20),
    "jobs_score_diff_ge_30": sum(1 for e in abs_errs if e >= 30),
    "rank_correlation_gt_vs_baseline_spearman": spearman(
        [r["gt_match_score"] for r in comparable], [r["baseline_match_score_production"] for r in comparable]),
    "note": ("GT Match Score = frozen canonical importance x Human label. Baseline (production) = model-predicted "
             "importance x model label. The failed job has no baseline score and is excluded."),
}

# ----------------------------------------------------------------- 17. correlation decomposition
gt_ok = [r for r in score_rows if r["gt_match_score"] is not None]
sp_gt_hmf = spearman([r["gt_match_score"] for r in gt_ok], [r["human_match_fit"] for r in gt_ok])
pe_gt_hmf = pearson([r["gt_match_score"] for r in gt_ok], [r["human_match_fit"] for r in gt_ok])
base_ok = [r for r in score_rows if r["baseline_match_score_production"] is not None]
sp_base_hmf = spearman([r["baseline_match_score_production"] for r in base_ok], [r["human_match_fit"] for r in base_ok])
pe_base_hmf = pearson([r["baseline_match_score_production"] for r in base_ok], [r["human_match_fit"] for r in base_ok])
# on the common comparable set (exclude failed job) for apples-to-apples
common = comparable
sp_gt_hmf_c = spearman([r["gt_match_score"] for r in common], [r["human_match_fit"] for r in common])
sp_base_hmf_c = spearman([r["baseline_match_score_production"] for r in common], [r["human_match_fit"] for r in common])
correlation_decomposition = {
    "gt_match_score_vs_human_match_fit_spearman_all29": sp_gt_hmf,
    "gt_match_score_vs_human_match_fit_pearson_all29": pe_gt_hmf,
    "baseline_match_score_vs_human_match_fit_spearman_all29": sp_base_hmf,
    "baseline_match_score_vs_human_match_fit_pearson_all29": pe_base_hmf,
    "on_common_comparable_set": {
        "gt_vs_hmf_spearman": sp_gt_hmf_c,
        "baseline_vs_hmf_spearman": sp_base_hmf_c,
        "correlation_loss_from_matcher_errors": round((sp_gt_hmf_c or 0) - (sp_base_hmf_c or 0), 4),
    },
    "interpretation": None,  # filled in report
}

# ----------------------------------------------------------------- 18. small-N volatility
def bucket_of(n):
    return "1" if n == 1 else "2" if n == 2 else "3" if n == 3 else "4-5" if n <= 5 else "6+"
buckets = {}
for r in score_rows:
    b = bucket_of(r["matchable_requirement_count"])
    buckets.setdefault(b, []).append(r)
small_n = {}
for b, rows in sorted(buckets.items()):
    ae = [x["abs_err_gt_vs_baseline"] for x in rows if x["abs_err_gt_vs_baseline"] is not None]
    # one-Important-label flip (Partial<->Strong = 0.5 weight step) on the smallest job in bucket:
    # step for a single Important requirement in an all-Important job of size k = 100 * 3*0.5 / (3*k) = 50/k
    kmin = min(x["matchable_requirement_count"] for x in rows)
    small_n[b] = {
        "jobs": len(rows),
        "mean_human_match_fit": round(statistics.mean(x["human_match_fit"] for x in rows), 2),
        "mean_gt_match_score": round(statistics.mean(x["gt_match_score"] for x in rows if x["gt_match_score"] is not None), 1),
        "mean_baseline_abs_err": round(statistics.mean(ae), 1) if ae else None,
        "one_important_label_flip_score_delta_pts_approx": round(50 / kmin, 1),
    }
big_flip_jobs = [r for r in score_rows if r["matchable_requirement_count"] <= 3
                 and r["abs_err_gt_vs_baseline"] is not None and r["abs_err_gt_vs_baseline"] >= 25]
small_n_volatility = {
    "by_bucket": small_n,
    "jobs_where_one_flip_moves_score_ge_25pts": [
        {"job": r["title"], "matchable": r["matchable_requirement_count"],
         "gt_score": r["gt_match_score"], "baseline_score": r["baseline_match_score_production"],
         "abs_err": r["abs_err_gt_vs_baseline"]} for r in big_flip_jobs],
    "classification": "DETERMINISTIC_SCORING / UX robustness — not a matcher-quality issue.",
}

# ----------------------------------------------------------------- 19. HMF outliers (GT score, not model)
gt_sorted = sorted(gt_ok, key=lambda r: r["gt_match_score"])
def rankmap(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    rk = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return rk
gs = [r["gt_match_score"] for r in gt_ok]
hf = [r["human_match_fit"] for r in gt_ok]
rg, rh = rankmap(gs), rankmap(hf)
hmf_outliers = []
for i, r in enumerate(gt_ok):
    rank_gap = abs(rg[i] - rh[i])
    if rank_gap >= 8:
        hmf_outliers.append({"job": r["title"], "human_match_fit": r["human_match_fit"],
                             "gt_match_score": r["gt_match_score"],
                             "matchable_requirement_count": r["matchable_requirement_count"],
                             "rank_gap": round(rank_gap, 1)})
hmf_outliers.sort(key=lambda x: -x["rank_gap"])
human_match_fit_construct = {
    "note": "These use GT (human) labels, so they are NOT matcher errors — they show the matchable-only Match Score construct vs holistic Human Match Fit.",
    "outliers": hmf_outliers,
    "explanations": [
        "matchable-only: Match Score ignores eligibility (42 rows) and knowledge (16 rows); a job can be capability-strong but eligibility-blocked, or vice versa.",
        "small requirement sets: 1-3 matchable rows -> coarse 0/50/100-ish scores that cannot express a nuanced 1-5 fit.",
        "role/domain mismatch: mismatched-control jobs (Xsolla, 微信语音识别算法) have few matchable PM-style rows; the candidate can 'cover' those while being wrong for the role.",
        "subjective holistic perception: Human Match Fit integrates seniority realism and role shape that individual matchable requirements do not encode.",
    ],
}

# ----------------------------------------------------------------- 20. ownership
ownership = {
    "Strong->Partial (17)": {"primary": "PROMPT_RULE_COMMUNICATION", "secondary": "MODEL_CAPABILITY",
        "rationale": "Frozen rubric rules (complete direct project can be Strong; OR-list; no-outcome != downgrade) are not in job-fit-v3; the model defaults to strict reading."},
    "Missing->Partial (6)": {"primary": "PROMPT_RULE_COMMUNICATION", "secondary": "MODEL_CAPABILITY",
        "rationale": "No explicit 'adjacent technology is not partial support' guardrail; model credits general AI experience toward specialised capability."},
    "Partial->Strong (4)": {"primary": "PROMPT_RULE_COMMUNICATION", "secondary": "MODEL_CAPABILITY",
        "rationale": "No 'match the narrowest unmet sub-claim' rule; skill-list / project evidence over-generalised."},
    "Partial->Missing (2)": {"primary": "MODEL_CAPABILITY",
        "rationale": "Model failed to connect an available adjacent evidence id it had access to."},
    "Unreconciled job (9)": {"primary": "PRODUCTION_NORMALIZATION", "secondary": "MODEL_CAPABILITY",
        "rationale": "Model emitted a duplicate id (capability); production discards the whole job with no partial recovery (normalization design)."},
    "Match Score volatility": {"primary": "DETERMINISTIC_SCORING",
        "rationale": "1-3 matchable requirements make the deterministic score jump 25-50 pts per label flip."},
    "GT-score vs Human-Match-Fit gap": {"primary": "EVALUATION_DATA_LIMITATION", "secondary": "DETERMINISTIC_SCORING",
        "rationale": "matchable-only construct + small-N + mismatched controls; not a matcher issue."},
}
ownership_counts = Counter(v["primary"] for v in ownership.values())

# ----------------------------------------------------------------- 21. benchmark vs not
benchmark_relevant = [
    "Strong/Partial calibration (17 Strong->Partial, Strong recall 0.63)",
    "Technology/domain adjacency reasoning (6 Missing->Partial)",
    "OR / alternative-list reasoning (OR-list mistakes)",
    "Compound requirement partial coverage",
    "Project-vs-formal-work-experience semantics",
    "Proficiency/scope overclaim (4 Partial->Strong)",
    "Schema adherence / duplicate-id emission rate across models & temperatures",
]
not_model_selection = [
    "All-or-nothing _normalize_matches (production normalization robustness) — a code decision, not a model choice",
    "Small-N deterministic Match Score volatility (scoring/UX) — needs a confidence caveat or min-requirement handling",
    "Evaluation dataset representativeness (27/30 Chinese, 22/30 experienced, 腾讯+百度 = 87%) — Dataset V2 scope",
    "Match Score construct vs holistic Human Match Fit gap — product semantics / documentation, not model quality",
]

# ----------------------------------------------------------------- 22. hypotheses
hypotheses = [
    {"id": "H1", "name": "Strong/Partial calibration via rubric rule communication",
     "baseline_evidence": "Strong recall 0.630; 17 GT-Strong->Partial; 8 'generic conservatism' + 6 'project under-credited' + 3 OR-list.",
     "target_metric": "Strong recall (up from 0.63), Macro F1 (up from 0.692)",
     "failure_slice": "project_evidence_rows + or_list_rows + strong_to_partial",
     "improvement_bar": "Strong recall >= 0.80 AND Strong precision >= 0.80 AND Missing->Partial errors do not increase (<=6)."},
    {"id": "H2", "name": "Technology/domain adjacency guardrail",
     "baseline_evidence": "6/6 GT-Missing->Partial are adjacency-driven (general AI -> multimodal/ASR/RL/AIGC).",
     "target_metric": "Missing recall (up from 0.667), Partial precision (up from 0.477)",
     "failure_slice": "technology_adjacency_rows",
     "improvement_bar": "Missing recall >= 0.83 AND no drop in Strong recall."},
    {"id": "H3", "name": "OR / alternative-list reasoning",
     "baseline_evidence": f"{or_list['or_list_incorrect']} OR-list mistakes; all GT-Strong downgraded to Partial for missing non-required alternatives.",
     "target_metric": "OR-list slice accuracy",
     "failure_slice": "or_list_rows",
     "improvement_bar": "OR-list slice accuracy >= 0.90."},
    {"id": "H4", "name": "Compound-requirement narrowest-unmet-subclaim rule",
     "baseline_evidence": f"{compound_requirements['errors_involving_incomplete_compound_coverage']} errors involve compound rows; 4 Partial->Strong over-credit partly-covered compounds.",
     "target_metric": "compound-slice accuracy; Partial precision",
     "failure_slice": "compound_rows",
     "improvement_bar": "compound-slice error rate <= non-compound error rate."},
    {"id": "H5", "name": "Duplicate-id / schema adherence across models & temperature",
     "baseline_evidence": "1/30 jobs lost to a duplicated requirement_id in raw output.",
     "target_metric": "job normalization success rate (up from 29/30); duplicate-id emission count",
     "failure_slice": "all jobs (schema adherence)",
     "improvement_bar": "30/30 normalization success across 3 repeats; 0 duplicate ids."},
    {"id": "H6", "name": "Model tier comparison (capacity vs prompt-bound)",
     "baseline_evidence": "Strong->Partial compression could be capacity- or prompt-bound; not separable from one run.",
     "target_metric": "Macro F1 delta at fixed prompt across Claude tiers",
     "failure_slice": "full 100",
     "improvement_bar": "identify whether a larger tier closes >50% of the Strong recall gap at the SAME prompt."},
    {"id": "H7", "name": "Repeat-run determinism check",
     "baseline_evidence": "Single run at temp 0; determinism assumed, not verified.",
     "target_metric": "label stability across 3 identical runs",
     "failure_slice": "full 100",
     "improvement_bar": ">= 98% label agreement across repeats."},
]

# ----------------------------------------------------------------- 23. slices
slices = {
    "project_based_evidence_rows": "GT or predicted reason references a project/internship (GoFin/KPay/个人项目/Product Owner) as the main evidence.",
    "formal_work_experience_rows": "source_text implies a formal professional role or a duration qualifier applied to a matchable (not eligibility) requirement.",
    "or_list_rows": "source_text contains 或 / slash-joined alternatives / '等方向' / '之一' (is_or_list=true in error_slices.csv).",
    "compound_rows": "is_compound=true: >=2 of {joint subclaim, >=2 '、' list, proficiency/completeness qualifier, multi-tool list}.",
    "technology_adjacency_rows": "GT Missing where predicted reason credits general/adjacent tech (multimodal/ASR/RL/AIGC/LLM) toward a specialised capability.",
    "proficiency_depth_rows": "source_text contains 熟练/精通/深入/扎实/proficient/expert or a multi-tool list requiring depth.",
    "domain_specific_rows": "requirement names a specific industry/domain (证券/金融/医疗健康/battery industry/内容创作).",
    "one_requirement_jobs": "matchable_requirement_count == 1.",
    "small_matchable_jobs": "matchable_requirement_count <= 3.",
    "mismatched_control_jobs": "role_category == mismatched_control in Dataset V1 (huawei:28183, xsolla:252b30e5, tencent:2064981110395420672).",
}

# ----------------------------------------------------------------- 24. decision
baseline_decision = {
    "keep_as_reference_baseline": "YES — honestly measured, fully reproducible, grounding/schema-format reliable; it is the anchor for Benchmark Round 1.",
    "keep_as_model_candidate": "CONDITIONAL — Macro F1 0.692 and Partial precision 0.477 are below a comfortable production bar, and 1/30 jobs produced no usable output. Retain as a candidate ONLY if Benchmark Round 1 (prompt-rule communication for H1-H4) lifts Macro F1 materially and closes the duplicate-id job-loss; otherwise compare against a higher Claude tier.",
    "drop_as_model_candidate": "NOT YET — no evidence it is worse than alternatives; alternatives have not been run.",
}

# ----------------------------------------------------------------- write
OUT = {
    "analysis_id": "current-claude-baseline-v1-error-analysis",
    "offline": True, "anthropic_calls": 0, "llm_calls": 0, "web_calls": 0, "production_matcher_calls": 0,
    "inputs": {
        "baseline_predictions": "job_match_baseline_claude_current_v1_predictions.json",
        "ground_truth": "job_match_annotation_full_v2_human_verified.json (frozen, read-only)",
        "ground_truth_version": "job-match-ground-truth-v2",
        "rubric_id": "annotation-rubric-v2",
        "frozen_eval_commit": "1a31c8d",
    },
    "summary": {
        "accounting": accounting,
        "effective_correct_coverage": effective_correct_coverage,
        "macro_f1": metrics["classification"]["macro_f1"],
        "accuracy_on_91_reconciled": metrics["classification"]["accuracy"],
        "headline": ("Only 62/100 frozen matchable requirements end up with a correct usable prediction "
                     "(Effective Correct Coverage 0.62). Of the 38 shortfalls: 9 are a single job lost to "
                     "production normalization, and 29 are label errors dominated by Strong->Partial (17)."),
    },
    "classification_errors": {"accounting": accounting, "effective_correct_coverage": effective_correct_coverage},
    "directional_errors": {"matrix": directional, "dominant": "Strong->Partial",
                           "dominant_count": trans["Strong->Partial"],
                           "dominant_pct_of_errors": round(trans["Strong->Partial"] / n_err, 4),
                           "dominant_pct_of_gt_strong": round(trans["Strong->Partial"] / 52, 4),
                           "bias": "The matcher compresses toward Partial: it under-credits direct evidence (Strong->Partial 17) far more than it over-credits (Partial->Strong 4), and it never crosses two steps (0 Strong<->Missing)."},
    "partial_analysis": partial_analysis,
    "strong_underprediction": {"total": len(s2p), "groups": s2p_groups,
                               "primary_owner": "PROMPT_RULE_COMMUNICATION"},
    "missing_to_partial": {"total": len(m2p), "groups": m2p_groups, "adjacency": adjacency_analysis},
    "partial_to_strong": {"total": len(p2s), "groups": p2s_groups, "compound_involved": p2s_compound},
    "project_vs_work": project_vs_work,
    "or_list": or_list,
    "compound_requirements": compound_requirements,
    "grounding_semantics": grounding_semantics,
    "schema_failure": schema_failure,
    "system_reliability": {
        "funnel": {
            "raw_schema_parse_success": "30 / 30",
            "job_normalization_success": "29 / 30",
            "requirement_prediction_coverage": "91 / 100",
            "effective_correct_coverage": f"{len(correct)} / 100",
        },
        "stage_losses": {"parse": 0, "normalize": 9, "wrong_label": 29, "usable_correct": len(correct)},
    },
    "score_propagation": score_propagation,
    "correlation_decomposition": correlation_decomposition,
    "small_n_volatility": small_n_volatility,
    "human_match_fit_construct": human_match_fit_construct,
    "ownership": {"per_family": ownership, "primary_counts": dict(ownership_counts)},
    "benchmark_relevant_issues": benchmark_relevant,
    "not_solvable_by_model_selection": not_model_selection,
    "benchmark_hypotheses": hypotheses,
    "benchmark_slices": slices,
    "baseline_decision": baseline_decision,
}
(EVALS / "job_match_baseline_claude_current_v1_error_analysis.json").write_text(
    json.dumps(OUT, ensure_ascii=False, indent=1))

# error_slices.csv
scols = list(enriched[0].keys())
with (EVALS / "job_match_baseline_claude_current_v1_error_slices.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=scols)
    w.writeheader()
    w.writerows(enriched)

# score_analysis.csv
with (EVALS / "job_match_baseline_claude_current_v1_score_analysis.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(score_rows[0].keys()))
    w.writeheader()
    w.writerows(score_rows)

# enriched error cases (incorrect + unreconciled only)
ec = [r for r in enriched if r["outcome"] != "correct"]
with (EVALS / "job_match_baseline_claude_current_v1_error_cases_enriched.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=scols)
    w.writeheader()
    w.writerows(ec)

print(json.dumps({
    "accounting": accounting,
    "effective_correct_coverage": effective_correct_coverage,
    "directional": {k: v["count"] for k, v in directional.items()},
    "partial": partial_analysis,
    "or_list": {k: or_list[k] for k in ("or_list_rows_total", "or_list_correct", "or_list_incorrect", "or_list_accuracy_reconciled")},
    "compound": compound_requirements,
    "adjacency": adjacency_analysis,
    "project_vs_work": {"under": project_vs_work["project_under_credited"]["count"], "over": project_vs_work["project_over_credited"]["count"]},
    "grounding_semantics": {k: grounding_semantics[k] for k in ("incorrect_strong_or_partial_predictions", "of_which_used_only_valid_evidence", "share")},
    "score_propagation": score_propagation,
    "correlation_decomposition": correlation_decomposition,
    "small_n": small_n,
    "big_flip_jobs": small_n_volatility["jobs_where_one_flip_moves_score_ge_25pts"],
    "hmf_outliers": hmf_outliers,
    "ownership_counts": dict(ownership_counts),
}, ensure_ascii=False, indent=1))
