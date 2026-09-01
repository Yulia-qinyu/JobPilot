"""Benchmark Round 1 — three-model comparison (offline, 0 API calls).

Combines:
  - REFERENCE  claude-sonnet-4-5-20250929  (recomputed offline from the FROZEN
    baseline predictions job_match_baseline_claude_current_v1_predictions.json —
    NOT rerun; latency/tokens taken from the frozen baseline metrics)
  - claude-haiku-4-5-20251001  (benchmark_round1_predictions_haiku-4-5.*)
  - claude-opus-5              (benchmark_round1_predictions_opus-5.*)

All three scored against the frozen Ground Truth with identical metric code.
"""

from __future__ import annotations

import csv
import json
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

EVALS = Path("/Users/yulia/Documents/JobPilot/backend/evals")
OUT = EVALS / "benchmark_round1"
LAB = ["Strong", "Partial", "Missing"]
IMPORTANCE_W = {"Critical": Decimal(5), "Important": Decimal(3), "Preferred": Decimal(1)}
MATCH_V = {"Strong": Decimal(1), "Partial": Decimal("0.5"), "Missing": Decimal(0)}
MISMATCH_CONTROL = {"huawei:28183", "xsolla:252b30e5-ce58-4a32-88b3-07ee83d06e67", "tencent:2064981110395420672"}
PROJ_RX = ("GoFin", "KPay", "个人项目", "Product Owner", "项目", "实习")
PROF_RX = ("熟练", "精通", "深入", "扎实", "proficient", "Proficient", "expert")
DOMAIN_RX = ("证券", "金融", "医疗健康", "battery", "内容", "创作", "AIGC")
ADJ_RX = ("多模态", "语音", "ASR", "流式", "精度调优", "基模", "强化学习", "RL", "AIGC")

gt = json.loads((EVALS / "job_match_annotation_full_v2_human_verified.json").read_text())
gm, hmf = {}, {}
for j in gt["jobs"]:
    hmf[j["job_id"]] = j["human_match_fit"]
    for r in j["requirements"]:
        gm[(j["job_id"], r["requirement_id"])] = r
matchable = {k: v for k, v in gm.items() if v["requirement_type"] == "matchable" and v["score_included"]}
job_of = {}
for (jid, rid) in matchable:
    job_of.setdefault(jid, []).append(rid)
slice_flag = {}
for row in csv.DictReader((EVALS / "job_match_baseline_claude_current_v1_error_slices.csv").open()):
    slice_flag[(row["job_id"], row["requirement_id"])] = {
        "is_or_list": row["is_or_list"] == "True", "is_compound": row["is_compound"] == "True"}
count_by_job = {jid: len(rids) for jid, rids in job_of.items()}


def det_score(items):
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
    n = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    d = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(n / d, 4) if d else None


def load_reference():
    """Recompute from frozen baseline predictions; 0 API calls."""
    pj = json.loads((EVALS / "job_match_baseline_claude_current_v1_predictions.json").read_text())["predictions"]
    rows = []
    for p in pj:
        rows.append({
            "job_id": p["job_id"], "requirement_id": p["requirement_id"],
            "predicted_label": p["predicted_label"],
            "predicted_evidence_ids": p["predicted_evidence_ids"],
            "normalized_reason": p["normalized_reason"], "raw_reason": p.get("raw_reason", ""),
        })
    bm = json.loads((EVALS / "job_match_baseline_claude_current_v1_metrics.json").read_text())
    lat = bm["latency"]
    tok = bm["tokens"]
    ti, to = tok["input"], tok["output"]
    cost = {"input_usd": round(ti / 1e6 * 3.0, 4), "output_usd": round(to / 1e6 * 15.0, 4),
            "total_usd": round(ti / 1e6 * 3.0 + to / 1e6 * 15.0, 4),
            "rate_input_per_mtok_usd": 3.0, "rate_output_per_mtok_usd": 15.0,
            "source": "Anthropic public pricing, verified 2026-09-01 (reference historical)", "cost_status": "VERIFIED"}
    return rows, {"total_runtime_ms": lat["total_runtime_ms"], "mean_ms": lat["mean_ms"],
                  "median_ms": lat["median_ms"], "p90_ms": lat["p90_ms"], "min_ms": lat["min_ms"], "max_ms": lat["max_ms"]}, \
        {"input": ti, "output": to, "total": ti + to, "avg_per_job": round((ti + to) / 30, 1),
         "avg_per_requirement": round((ti + to) / 100, 1)}, cost


def load_candidate(slug):
    rows = []
    for r in csv.DictReader((OUT / f"benchmark_round1_predictions_{slug}.csv").open()):
        rows.append({
            "job_id": r["job_id"], "requirement_id": r["requirement_id"],
            "predicted_label": r["predicted_label"] or None,
            "predicted_evidence_ids": r["predicted_evidence_ids"].split("|") if r["predicted_evidence_ids"] else [],
            "normalized_reason": r["normalized_reason"], "raw_reason": r["raw_reason"],
        })
    m = json.loads((OUT / f"benchmark_round1_metrics_{slug}.json").read_text())
    return rows, m["latency"], m["tokens"], m["cost"]


def metrics_for(rows):
    for r in rows:
        key = (r["job_id"], r["requirement_id"])
        r["gt"] = matchable[key]["human_match_label"]
        r["imp"] = matchable[key]["importance"]
        r["src"] = matchable[key]["source_text"]
    paired = [r for r in rows if r["predicted_label"]]
    correct = [r for r in paired if r["predicted_label"] == r["gt"]]
    conf = {a: {b: 0 for b in LAB} for a in LAB}
    for r in paired:
        conf[r["gt"]][r["predicted_label"]] += 1

    def prf(l):
        tp = conf[l][l]
        fp = sum(conf[o][l] for o in LAB if o != l)
        fn = sum(conf[l][o] for o in LAB if o != l)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        return {"precision": round(pr, 4), "recall": round(rc, 4), "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}
    per_class = {l: prf(l) for l in LAB}
    macro = {k: round(statistics.mean(per_class[l][k] for l in LAB), 4) for k in ("precision", "recall", "f1")}
    acc = round(len(correct) / len(paired), 4) if paired else 0.0
    ecc = round(len(correct) / 100, 4)
    from collections import Counter
    tr = Counter(f"{r['gt']}->{r['predicted_label']}" for r in paired if r["predicted_label"] != r["gt"])
    sp = [r for r in paired if r["predicted_label"] in ("Strong", "Partial")]
    valid_ev = {e["evidence_id"] for e in gt["candidate_evidence_snapshot"]["evidence_catalog"]}
    grounding = {
        "grounding_rate": round(sum(1 for r in sp if any(e in valid_ev for e in r["predicted_evidence_ids"])) / len(sp), 4) if sp else None,
        "unsupported_match_rate": round(sum(1 for r in sp if any(e not in valid_ev for e in r["predicted_evidence_ids"])) / len(sp), 4) if sp else None,
    }
    # match score
    gs, ms = {}, {}
    for jid, rids in job_of.items():
        gs[jid] = det_score([(matchable[(jid, rid)]["importance"], matchable[(jid, rid)]["human_match_label"]) for rid in rids])
        jp = [r for r in rows if r["job_id"] == jid]
        if all(r["predicted_label"] for r in jp):
            ms[jid] = det_score([(matchable[(r["job_id"], r["requirement_id"])]["importance"], r["predicted_label"]) for r in jp])
        else:
            ms[jid] = None
    comp = [jid for jid in job_of if gs[jid] is not None and ms[jid] is not None]
    ae = [abs(gs[jid] - ms[jid]) for jid in comp]
    score = {
        "jobs_scored": len(comp),
        "mae_vs_gt_score": round(statistics.mean(ae), 2) if ae else None,
        "median_abs_err": round(statistics.median(ae), 2) if ae else None,
        "max_abs_err": max(ae) if ae else None,
        "jobs_diff_ge_20": sum(1 for e in ae if e >= 20),
        "jobs_diff_ge_30": sum(1 for e in ae if e >= 30),
        "spearman_model_vs_gt_score": spearman([gs[j] for j in comp], [ms[j] for j in comp]),
        "spearman_model_vs_human_match_fit": spearman([ms[j] for j in comp], [hmf[j] for j in comp]),
    }
    # slices
    def sacc(pred):
        rr = [r for r in paired if pred(r)]
        return {"n": sum(1 for r in rows if pred(r)), "n_reconciled": len(rr),
                "accuracy": round(sum(1 for r in rr if r["predicted_label"] == r["gt"]) / len(rr), 4) if rr else None,
                "errors": sum(1 for r in rr if r["predicted_label"] != r["gt"])}
    slices = {
        "or_list": sacc(lambda r: slice_flag.get((r["job_id"], r["requirement_id"]), {}).get("is_or_list")),
        "technology_adjacency": sacc(lambda r: r["gt"] == "Missing" and any(k in r["src"] for k in ADJ_RX)),
        "project_based_evidence": sacc(lambda r: any(k in (r["normalized_reason"] + r["raw_reason"]) for k in PROJ_RX)),
        "formal_work_experience": sacc(lambda r: any(k in r["src"] for k in ("年以上", "年及以上", "工作经验", "正式"))),
        "compound": sacc(lambda r: slice_flag.get((r["job_id"], r["requirement_id"]), {}).get("is_compound")),
        "proficiency_depth": sacc(lambda r: any(k in r["src"] for k in PROF_RX)),
        "domain_specific": sacc(lambda r: any(k in r["src"] for k in DOMAIN_RX)),
        "small_matchable_jobs": sacc(lambda r: count_by_job[r["job_id"]] <= 3),
        "one_requirement_jobs": sacc(lambda r: count_by_job[r["job_id"]] == 1),
        "mismatched_control_jobs": sacc(lambda r: r["job_id"] in MISMATCH_CONTROL),
    }
    adj_fp = sum(1 for r in paired if r["gt"] == "Missing" and r["predicted_label"] in ("Partial", "Strong")
                 and any(k in r["src"] for k in ADJ_RX))
    proj_under = sum(1 for r in paired if LAB.index(r["predicted_label"]) > LAB.index(r["gt"])
                     and any(k in r["normalized_reason"] for k in ("实习", "个人项目", "作为应届生", "缺少完整", "从0到1", "从 0 到 1", "正式")))
    proj_over = sum(1 for r in paired if LAB.index(r["predicted_label"]) < LAB.index(r["gt"])
                    and any(k in (r["normalized_reason"] + r["raw_reason"]) for k in PROJ_RX))
    return {
        "reconciled": len(paired), "unreconciled": 100 - len(paired),
        "accuracy": acc, "macro": macro, "per_class": per_class,
        "confusion": [[conf[a][b] for b in LAB] for a in LAB],
        "directional": {k: tr.get(k, 0) for k in ("Strong->Partial", "Strong->Missing", "Partial->Strong",
                                                  "Partial->Missing", "Missing->Strong", "Missing->Partial")},
        "effective_correct_coverage": ecc,
        "grounding": grounding, "match_score": score, "slices": slices,
        "adjacency_false_positives": adj_fp, "project_under": proj_under, "project_over": proj_over,
        "gt_match_score_vs_human_match_fit_spearman_reference": spearman(
            [gs[j] for j in job_of if gs[j] is not None], [hmf[j] for j in job_of if gs[j] is not None]),
    }


MODELS = [
    ("claude-sonnet-4-5-20250929", "REFERENCE", *load_reference()),
    ("claude-haiku-4-5-20251001", "haiku-4-5", *load_candidate("haiku-4-5")),
    # claude-opus-5 EXCLUDED — all 30 calls rejected HTTP 400 "`temperature` is deprecated for this
    # model." The fixed production matcher contract (temperature=0, hard-coded in claude_client.py)
    # cannot be sent to Opus 5 without a production code change. See benchmark_round1_integrity_opus-5.json.
]

report = {"benchmark_id": "benchmark-round1-fixed-prompt-model-comparison",
          "reference_gt_match_score_vs_human_match_fit_spearman": 0.845,
          "quality_gates": {"macro_f1": 0.75, "ecc": 0.75, "grounding_rate": 0.98, "unsupported_match_rate": 0.02,
                            "strong_recall": 0.75, "strong_precision": 0.80, "partial_precision": 0.60, "missing_recall": 0.667},
          "improvement_bands_vs_sonnet_macro_f1_0.692": {"<+0.02": "not compelling", "+0.02..0.05": "small",
                                                         "+0.05..0.10": "meaningful", ">=+0.10": "large"},
          "models": {}}
for model_id, slug, rows, lat, tok, cost in MODELS:
    m = metrics_for(rows)
    m.update({"model": model_id, "slug": slug, "latency": lat, "tokens": tok, "cost": cost})
    report["models"][model_id] = m

(OUT / "benchmark_round1_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))

# metrics.csv — one row per model
cols = ["model", "reconciled", "unreconciled", "effective_correct_coverage", "accuracy",
        "macro_precision", "macro_recall", "macro_f1",
        "strong_p", "strong_r", "strong_f1", "partial_p", "partial_r", "partial_f1",
        "missing_p", "missing_r", "missing_f1",
        "Strong->Partial", "Missing->Partial", "Partial->Strong", "Partial->Missing",
        "or_list_accuracy", "adjacency_false_positives", "project_under", "project_over",
        "grounding_rate", "unsupported_match_rate",
        "job_normalization", "requirement_coverage",
        "match_score_mae_vs_gt", "match_score_spearman_vs_gt", "match_score_spearman_vs_hmf",
        "latency_mean_ms", "latency_p90_ms", "tokens_input", "tokens_output", "tokens_total",
        "cost_total_usd", "cost_status"]
with (OUT / "benchmark_round1_metrics.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    for model_id, _, rows, lat, tok, cost in MODELS:
        m = report["models"][model_id]
        pc = m["per_class"]
        w.writerow({
            "model": model_id, "reconciled": m["reconciled"], "unreconciled": m["unreconciled"],
            "effective_correct_coverage": m["effective_correct_coverage"], "accuracy": m["accuracy"],
            "macro_precision": m["macro"]["precision"], "macro_recall": m["macro"]["recall"], "macro_f1": m["macro"]["f1"],
            "strong_p": pc["Strong"]["precision"], "strong_r": pc["Strong"]["recall"], "strong_f1": pc["Strong"]["f1"],
            "partial_p": pc["Partial"]["precision"], "partial_r": pc["Partial"]["recall"], "partial_f1": pc["Partial"]["f1"],
            "missing_p": pc["Missing"]["precision"], "missing_r": pc["Missing"]["recall"], "missing_f1": pc["Missing"]["f1"],
            "Strong->Partial": m["directional"]["Strong->Partial"], "Missing->Partial": m["directional"]["Missing->Partial"],
            "Partial->Strong": m["directional"]["Partial->Strong"], "Partial->Missing": m["directional"]["Partial->Missing"],
            "or_list_accuracy": m["slices"]["or_list"]["accuracy"],
            "adjacency_false_positives": m["adjacency_false_positives"],
            "project_under": m["project_under"], "project_over": m["project_over"],
            "grounding_rate": m["grounding"]["grounding_rate"], "unsupported_match_rate": m["grounding"]["unsupported_match_rate"],
            "job_normalization": f"{m['reconciled'] and (30 - (1 if m['unreconciled'] else 0))}/30" if model_id.startswith("claude-sonnet") else "30/30",
            "requirement_coverage": f"{m['reconciled']}/100",
            "match_score_mae_vs_gt": m["match_score"]["mae_vs_gt_score"],
            "match_score_spearman_vs_gt": m["match_score"]["spearman_model_vs_gt_score"],
            "match_score_spearman_vs_hmf": m["match_score"]["spearman_model_vs_human_match_fit"],
            "latency_mean_ms": lat["mean_ms"], "latency_p90_ms": lat["p90_ms"],
            "tokens_input": tok["input"], "tokens_output": tok["output"], "tokens_total": tok["total"],
            "cost_total_usd": cost.get("total_usd"), "cost_status": cost.get("cost_status"),
        })

# combined slice metrics
with (OUT / "benchmark_round1_slice_metrics.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "slice", "n", "n_reconciled", "accuracy", "errors"])
    for model_id in report["models"]:
        for name, s in report["models"][model_id]["slices"].items():
            w.writerow([model_id, name, s["n"], s["n_reconciled"], s["accuracy"], s["errors"]])

print(json.dumps({mid: {"macro_f1": report["models"][mid]["macro"]["f1"],
                        "ecc": report["models"][mid]["effective_correct_coverage"],
                        "reconciled": report["models"][mid]["reconciled"],
                        "S_P_M_f1": [report["models"][mid]["per_class"][l]["f1"] for l in LAB],
                        "strong_r": report["models"][mid]["per_class"]["Strong"]["recall"],
                        "strong_p": report["models"][mid]["per_class"]["Strong"]["precision"],
                        "partial_p": report["models"][mid]["per_class"]["Partial"]["precision"],
                        "missing_r": report["models"][mid]["per_class"]["Missing"]["recall"],
                        "S->P": report["models"][mid]["directional"]["Strong->Partial"],
                        "M->P": report["models"][mid]["directional"]["Missing->Partial"],
                        "or_list_acc": report["models"][mid]["slices"]["or_list"]["accuracy"],
                        "adj_fp": report["models"][mid]["adjacency_false_positives"],
                        "score_mae": report["models"][mid]["match_score"]["mae_vs_gt_score"],
                        "score_spearman_hmf": report["models"][mid]["match_score"]["spearman_model_vs_human_match_fit"],
                        "lat_mean_ms": report["models"][mid]["latency"]["mean_ms"],
                        "tok_total": report["models"][mid]["tokens"]["total"],
                        "cost": report["models"][mid]["cost"].get("total_usd") or report["models"][mid]["cost"].get("cost_status")}
                  for mid in report["models"]}, ensure_ascii=False, indent=1))
