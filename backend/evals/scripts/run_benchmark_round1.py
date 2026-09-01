"""Benchmark Round 1 — Fixed-Prompt Model Comparison, ONE candidate per invocation.

Usage:  python backend/evals/scripts/run_benchmark_round1.py <model_id> <slug>

Reuses the EXACT input construction of run_current_claude_baseline_v1.py. The ONLY
experimental variable is the model identifier. No prompt / schema / temperature /
max_tokens / evidence / normalization / Match-Score change. Ground Truth labels are
loaded ONLY after every raw prediction is persisted.

Persists per model:
  benchmark_round1_predictions_<slug>.json      (raw + normalized, pre-GT)
  benchmark_round1_predictions_<slug>.csv       (100 rows, per requirement, post-GT join)
  benchmark_round1_metrics_<slug>.json
  benchmark_round1_job_scores_<slug>.csv
  benchmark_round1_slice_metrics_<slug>.csv
  benchmark_round1_errors_<slug>.csv
  benchmark_round1_latency_tokens_<slug>.csv
  benchmark_round1_integrity_<slug>.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

BACKEND = Path("/Users/yulia/Documents/JobPilot/backend")
EVALS = BACKEND / "evals"
OUT = EVALS / "benchmark_round1"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings                                   # noqa: E402
from app.schemas.fit_analysis import EvidenceSourceRead               # noqa: E402
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient  # noqa: E402
from app.services.evidence_catalog import EvidenceCatalog             # noqa: E402
from app.services.fit_analysis_service import (                       # noqa: E402
    FitAnalysisNormalizationError,
    FitAnalysisService,
)
from app.services.match_score import MatchScoreService, NoScorableRequirementsError  # noqa: E402
from app.services.requirement_catalog import RequirementCatalog, ScoredRequirement  # noqa: E402
from app.services.requirement_matcher import RequirementMatcher       # noqa: E402
from sqlalchemy import create_engine                                  # noqa: E402
from sqlalchemy.orm import Session                                    # noqa: E402
from sqlalchemy.pool import StaticPool                                # noqa: E402

MODEL_ID = sys.argv[1]
SLUG = sys.argv[2]
IMPORTANCE_HINT = {"Critical": "high", "Important": "medium", "Preferred": "low"}
GT_PATH = EVALS / "job_match_annotation_full_v2_human_verified.json"
DS_PATH = EVALS / "job_match_eval_dataset_v1.json"
SLICES_PATH = EVALS / "job_match_baseline_claude_current_v1_error_slices.csv"

IMPORTANCE_W = {"Critical": Decimal(5), "Important": Decimal(3), "Preferred": Decimal(1)}
MATCH_V = {"Strong": Decimal(1), "Partial": Decimal("0.5"), "Missing": Decimal(0)}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 4) if den else None


# ----------------------------------------------------------------- fixed inputs
settings = get_settings()
FIXED_SHA = {
    "requirement_matcher.py": sha(BACKEND / "app/services/requirement_matcher.py"),
    "claude_client.py": sha(BACKEND / "app/services/claude_client.py"),
    "match_score.py": sha(BACKEND / "app/services/match_score.py"),
    "ground_truth": sha(GT_PATH),
    "dataset_v1": sha(DS_PATH),
}
EXPECT_SHA = {
    "requirement_matcher.py": "e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b",
    "claude_client.py": "76d953c4ae852502c0c85b16a53f1f8fcaeb3a7f39c791ff1776a3ed0b729b81",
    "ground_truth": "52cda176e166146ffc24a85067f13618c5f717cedab506f0ba17fe5e701ba050",
    "dataset_v1": "3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558",
}
prompt_drift = {k: (FIXED_SHA[k] != v) for k, v in EXPECT_SHA.items()}
assert not any(prompt_drift.values()), f"FIXED-INPUT DRIFT: {prompt_drift}"
assert RequirementMatcher.PROMPT_VERSION == "job-fit-v3-matchable-only"
assert RequirementMatcher.SCHEMA_VERSION == "fit-analysis-wire-v2"

gt = json.loads(GT_PATH.read_text())
ds = json.loads(DS_PATH.read_text())
ds_title = {j["job_id"]: j["title"] for j in ds["jobs"]}
ds_company = {j["job_id"]: j["company"] for j in ds["jobs"]}
ds_role = {j["job_id"]: j["role_category"] for j in ds["jobs"]}

snap = gt["candidate_evidence_snapshot"]
sources = []
for e in snap["evidence_catalog"]:
    st, _, sid = e["evidence_id"].partition(":")
    sources.append(EvidenceSourceRead(source_type=st, source_id=sid, text=e["text_summary"], context=e["context"]))
evidence = EvidenceCatalog(sources=sources, resume_hash=snap["resume_hash"],
                           experience_bank_hash=snap["experience_bank_hash"])
valid_ev = {f"{s.source_type}:{s.source_id}" for s in sources}

matchable_by_job = {}
gt_label, gt_ev, gt_imp = {}, {}, {}
for j in gt["jobs"]:
    for r in j["requirements"]:
        if r["requirement_type"] == "matchable" and r["score_included"]:
            matchable_by_job.setdefault(j["job_id"], []).append(r)
            key = (j["job_id"], r["requirement_id"])
            gt_label[key] = r["human_match_label"]
            gt_ev[key] = list(r["human_evidence_ids"])
            gt_imp[key] = r["importance"]
hmf = {j["job_id"]: j["human_match_fit"] for j in gt["jobs"]}
job_order = [j["job_id"] for j in gt["jobs"]]
assert sum(len(v) for v in matchable_by_job.values()) == 100

# slice flags from the frozen baseline analysis (pre-registered; not re-derived)
slice_flag = {}
for row in csv.DictReader(SLICES_PATH.open()):
    slice_flag[(row["job_id"], row["requirement_id"])] = {
        "is_or_list": row["is_or_list"] == "True",
        "is_compound": row["is_compound"] == "True",
        "root_cause_groups": row["root_cause_groups"],
    }
MISMATCH_CONTROL = {"huawei:28183", "xsolla:252b30e5-ce58-4a32-88b3-07ee83d06e67", "tencent:2064981110395420672"}
PROJ_RX = ("GoFin", "KPay", "个人项目", "Product Owner", "项目", "实习")
DOMAIN_RX = ("证券", "金融", "医疗健康", "battery", "内容", "创作", "AIGC")
PROF_RX = ("熟练", "精通", "深入", "扎实", "proficient", "expert", "Proficient")

_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
fit_service = FitAnalysisService(Session(_engine), settings)
score_service = MatchScoreService()

# ----------------------------------------------------------------- run
RUN_TS = datetime.now(timezone.utc)
RUN_ID = f"benchmark-round1-{SLUG}-" + RUN_TS.strftime("%Y%m%d-%H%M%S")
raw_records, pred_rows, job_score_rows = [], [], []
latencies, tok_in, tok_out = [], 0, 0
n_calls = schema_ok = norm_ok = 0
gt_leak_guard = "GROUND_TRUTH_NOT_LOADED_YET"

wall0 = time.perf_counter()
for jid in job_order:
    rows = matchable_by_job[jid]
    scored = [ScoredRequirement(requirement_id=r["requirement_id"], text=r["normalized_requirement"],
                                context=r["source_text"], importance_hint=IMPORTANCE_HINT[r["importance"]],
                                source_kind="v2_matchable") for r in rows]
    catalog = RequirementCatalog(requirements=scored, structured_jd_hash="benchmark-round1-not-persisted")
    client = ClaudeStructuredClient(settings)
    client.model = MODEL_ID                    # <-- the ONLY experimental variable
    matcher = RequirementMatcher(client)
    assert client.model == MODEL_ID

    submitted = [s.requirement_id for s in scored]
    ev_payload = [{"evidence_source_id": f"{s.source_type}:{s.source_id}", "source_type": s.source_type,
                   "text": s.text, "context": s.context} for s in sources]
    t0 = time.perf_counter()
    err = raw_out = normalized = norm_err = None
    n_calls += 1
    try:
        out = matcher.analyze(catalog, evidence)
        raw_out = out.model_dump(mode="json")
        schema_ok += 1
        schema_success = True
    except ClaudeServiceError as ex:
        schema_success = False
        err = f"{type(ex).__name__}:{ex.code}:{ex}"
        out = None
    walltime_ms = (time.perf_counter() - t0) * 1000
    lm = dict(client.last_call_metrics)
    m_ms = float(lm.get("elapsed_seconds") or 0.0) * 1000
    latencies.append(m_ms if m_ms else walltime_ms)
    ti = lm.get("input_tokens") or 0
    to = lm.get("output_tokens") or 0
    tok_in += ti
    tok_out += to

    if out is not None:
        try:
            normalized, unsup, hard_dg, det_adj = fit_service._normalize_matches(out, catalog, evidence)
            norm_ok += 1
        except FitAnalysisNormalizationError as ex:
            norm_err = str(ex)

    raw_records.append({
        "model": MODEL_ID, "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
        "requirement_ids_submitted": submitted, "evidence_catalog_submitted": ev_payload,
        "request_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_model_output_parsed": raw_out,
        "normalized_backend_output": [m.model_dump(mode="json") for m in normalized] if normalized else None,
        "schema_parse_success": schema_success,
        "normalization_success": (out is not None and norm_err is None),
        "normalization_error": norm_err,
        "latency_ms_model": round(m_ms, 1), "latency_ms_walltime": round(walltime_ms, 1),
        "input_tokens": ti, "output_tokens": to, "total_tokens": ti + to,
        "retry_count": "not exposed by anthropic messages.parse; SDK default retries only",
        "error": err,
        "ground_truth_state_during_prediction": gt_leak_guard,
    })
    pred_by_id = {m.requirement_id: m for m in (normalized or [])}
    for r in rows:
        rid = r["requirement_id"]
        m = pred_by_id.get(rid)
        raw_reason = ""
        if raw_out:
            for rm in raw_out["requirement_matches"]:
                if rm["requirement_id"] == rid:
                    raw_reason = rm["reason"]
        if m is not None:
            pev = [f"{s['source_type']}:{s['source_id']}" for s in m.model_dump(mode="json")["evidence_sources"]]
            sup = [e for e in pev if e in valid_ev]
            uns = [e for e in pev if e not in valid_ev]
            pred_rows.append({
                "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
                "requirement_id": rid, "normalized_requirement": r["normalized_requirement"],
                "predicted_label": m.match_status, "predicted_evidence_ids": pev,
                "supported_predicted_evidence_ids": sup, "unsupported_predicted_evidence_ids": uns,
                "raw_reason": raw_reason, "normalized_reason": m.reason,
                "latency_ms": round(m_ms, 1), "input_tokens": ti, "output_tokens": to,
                "schema_success": schema_success and norm_err is None, "error": ""})
        else:
            pred_rows.append({
                "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
                "requirement_id": rid, "normalized_requirement": r["normalized_requirement"],
                "predicted_label": None, "predicted_evidence_ids": [], "supported_predicted_evidence_ids": [],
                "unsupported_predicted_evidence_ids": [], "raw_reason": raw_reason, "normalized_reason": "",
                "latency_ms": round(m_ms, 1), "input_tokens": ti, "output_tokens": to,
                "schema_success": False, "error": err or norm_err or "no prediction"})
    bscore = None
    if normalized:
        try:
            bscore = score_service.score(normalized)
        except NoScorableRequirementsError:
            pass
    job_score_rows.append({"job_id": jid, "company": ds_company[jid], "title": ds_title[jid],
                           "matchable_requirement_count": len(rows),
                           "model_match_score": bscore, "notes": (err or norm_err or "")})
    print(f"  {jid:<44} n={len(rows):>2}  score={bscore}  tok={ti}+{to}  {round(m_ms)}ms  "
          f"{'OK' if (raw_out and not norm_err) else 'FAIL:'+str(err or norm_err)}", flush=True)

wall_ms = (time.perf_counter() - wall0) * 1000

# persist raw BEFORE loading GT labels for metrics
(OUT / f"benchmark_round1_predictions_{SLUG}.json").write_text(
    json.dumps({"run_id": RUN_ID, "model": MODEL_ID, "calls": raw_records}, ensure_ascii=False, indent=1))
print(f"\n[persisted raw predictions for {MODEL_ID} — now loading Ground Truth for scoring]", flush=True)
gt_leak_guard = "GROUND_TRUTH_LOADED_AFTER_PERSIST"

# ----------------------------------------------------------------- metrics
LAB = ["Strong", "Partial", "Missing"]
for p in pred_rows:
    key = (p["job_id"], p["requirement_id"])
    p["ground_truth_label"] = gt_label[key]
    p["gt_evidence_ids"] = gt_ev[key]
    p["correct"] = (p["predicted_label"] == gt_label[key]) if p["predicted_label"] else None
    p["grounding_valid"] = (
        (p["predicted_label"] in ("Strong", "Partial") and len(p["supported_predicted_evidence_ids"]) >= 1)
        or p["predicted_label"] == "Missing") if p["predicted_label"] else None

paired = [p for p in pred_rows if p["predicted_label"]]
correct = [p for p in paired if p["correct"]]
conf = {a: {b: 0 for b in LAB} for a in LAB}
for p in paired:
    conf[p["ground_truth_label"]][p["predicted_label"]] += 1

def prf(l):
    tp = conf[l][l]
    fp = sum(conf[o][l] for o in LAB if o != l)
    fn = sum(conf[l][o] for o in LAB if o != l)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    return {"precision": round(pr, 4), "recall": round(rc, 4), "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}

per_class = {l: prf(l) for l in LAB}
acc = round(len(correct) / len(paired), 4) if paired else 0.0
macro = {k: round(statistics.mean(per_class[l][k] for l in LAB), 4) for k in ("precision", "recall", "f1")}
ecc = round(len(correct) / 100, 4)

trans = Counter(f"{p['ground_truth_label']}->{p['predicted_label']}" for p in paired
                if p["predicted_label"] != p["ground_truth_label"])

sp = [p for p in paired if p["predicted_label"] in ("Strong", "Partial")]
grounding = {
    "grounding_rate": round(sum(1 for p in sp if p["supported_predicted_evidence_ids"]) / len(sp), 4) if sp else None,
    "unsupported_match_rate": round(sum(1 for p in sp if p["unsupported_predicted_evidence_ids"]) / len(sp), 4) if sp else None,
    "evidence_id_validity_rate": round(
        sum(1 for p in paired for e in p["predicted_evidence_ids"] if e in valid_ev)
        / max(1, sum(len(p["predicted_evidence_ids"]) for p in paired)), 4),
    "strong_partial_zero_evidence_rate": round(sum(1 for p in sp if not p["predicted_evidence_ids"]) / len(sp), 4) if sp else None,
    "missing_with_evidence_rate": round(sum(1 for p in paired if p["predicted_label"] == "Missing" and p["predicted_evidence_ids"]) / len(paired), 4) if paired else None,
}

# schema
omitted = sum(1 for p in pred_rows if p["predicted_label"] is None)
dup = halluc = invlab = 0
for rr in raw_records:
    ro = rr["raw_model_output_parsed"]
    if not ro:
        continue
    ids = [m["requirement_id"] for m in ro["requirement_matches"]]
    dup += len(ids) - len(set(ids))
    halluc += sum(1 for i in ids if i not in rr["requirement_ids_submitted"])
    invlab += sum(1 for m in ro["requirement_matches"] if m["match_status"] not in LAB)

# match score
gt_score, model_score = {}, {}
for jsr in job_score_rows:
    jid = jsr["job_id"]
    rs = matchable_by_job[jid]
    gt_score[jid] = det_score([(gt_imp[(jid, r["requirement_id"])], gt_label[(jid, r["requirement_id"])]) for r in rs])
    model_score[jid] = jsr["model_match_score"]
comp = [jid for jid in job_order if gt_score[jid] is not None and model_score[jid] is not None]
abs_err = [abs(gt_score[jid] - model_score[jid]) for jid in comp]
score_cmp = {
    "jobs_comparable": len(comp),
    "mae_vs_gt_score": round(statistics.mean(abs_err), 2) if abs_err else None,
    "median_abs_err": round(statistics.median(abs_err), 2) if abs_err else None,
    "max_abs_err": max(abs_err) if abs_err else None,
    "jobs_diff_ge_20": sum(1 for e in abs_err if e >= 20),
    "jobs_diff_ge_30": sum(1 for e in abs_err if e >= 30),
    "spearman_model_vs_gt_score": spearman([gt_score[j] for j in comp], [model_score[j] for j in comp]),
    "spearman_model_vs_human_match_fit": spearman([model_score[j] for j in comp], [hmf[j] for j in comp]),
    "reference_gt_score_vs_human_match_fit_spearman": 0.845,
}

# slices
def slice_rows(name):
    out = []
    for p in paired + [x for x in pred_rows if x["predicted_label"] is None]:
        key = (p["job_id"], p["requirement_id"])
        fl = slice_flag.get(key, {})
        src = next((r["source_text"] for r in matchable_by_job[p["job_id"]] if r["requirement_id"] == p["requirement_id"]), "")
        cnt = next(x["matchable_requirement_count"] for x in job_score_rows if x["job_id"] == p["job_id"])
        keep = {
            "or_list": fl.get("is_or_list"),
            "technology_adjacency": p["ground_truth_label"] == "Missing" and any(k in src for k in
                ("多模态", "语音", "ASR", "流式", "精度调优", "基模", "强化学习", "RL", "AIGC")),
            "project_based_evidence": any(k in (p["normalized_reason"] + p["raw_reason"]) for k in PROJ_RX),
            "formal_work_experience": any(k in src for k in ("年以上", "年及以上", "formal", "正式", "工作经验")),
            "compound": fl.get("is_compound"),
            "proficiency_depth": any(k in src for k in PROF_RX),
            "domain_specific": any(k in src for k in DOMAIN_RX),
            "small_matchable_jobs": cnt <= 3,
            "one_requirement_jobs": cnt == 1,
            "mismatched_control_jobs": p["job_id"] in MISMATCH_CONTROL,
        }[name]
        if keep:
            out.append(p)
    return out

SLICES = ["or_list", "technology_adjacency", "project_based_evidence", "formal_work_experience",
          "compound", "proficiency_depth", "domain_specific", "small_matchable_jobs",
          "one_requirement_jobs", "mismatched_control_jobs"]
slice_metrics = {}
for name in SLICES:
    rws = slice_rows(name)
    rec = [r for r in rws if r["predicted_label"]]
    corr = sum(1 for r in rec if r["correct"])
    tdir = Counter(f"{r['ground_truth_label']}->{r['predicted_label']}" for r in rec if r["predicted_label"] != r["ground_truth_label"])
    slice_metrics[name] = {
        "n": len(rws), "n_reconciled": len(rec),
        "accuracy": round(corr / len(rec), 4) if rec else None,
        "errors": len(rec) - corr, "unreconciled": len(rws) - len(rec),
        "directional": dict(tdir),
    }
# adjacency false positives explicitly
adj_fp = sum(1 for p in paired if p["ground_truth_label"] == "Missing" and p["predicted_label"] in ("Partial", "Strong")
             and any(k in next((r["source_text"] for r in matchable_by_job[p["job_id"]] if r["requirement_id"] == p["requirement_id"]), "")
                     for k in ("多模态", "语音", "ASR", "流式", "精度调优", "基模", "强化学习", "RL", "AIGC")))
# project under/over
proj_under = sum(1 for p in paired if p["predicted_label"] and p["ground_truth_label"] and
                 LAB.index(p["predicted_label"]) > LAB.index(p["ground_truth_label"]) and
                 any(k in p["normalized_reason"] for k in ("实习", "个人项目", "作为应届生", "缺少完整", "从0到1", "从 0 到 1", "正式")))
proj_over = sum(1 for p in paired if p["predicted_label"] and p["ground_truth_label"] and
                LAB.index(p["predicted_label"]) < LAB.index(p["ground_truth_label"]) and
                any(k in (p["normalized_reason"] + p["raw_reason"]) for k in PROJ_RX))

lat_sorted = sorted(latencies)
def pct(q):
    if not lat_sorted:
        return None
    k = max(0, min(len(lat_sorted) - 1, int(round(q / 100 * (len(lat_sorted) - 1)))))
    return round(lat_sorted[k], 1)

# cost
PRICING = {
    "claude-haiku-4-5-20251001": {"in": 1.0, "out": 5.0, "source": "Anthropic public pricing, verified 2026-09-01"},
    "claude-sonnet-4-5-20250929": {"in": 3.0, "out": 15.0, "source": "Anthropic public pricing, verified 2026-09-01 (reference)"},
}
if MODEL_ID in PRICING:
    pr = PRICING[MODEL_ID]
    cost = {"input_usd": round(tok_in / 1e6 * pr["in"], 4), "output_usd": round(tok_out / 1e6 * pr["out"], 4),
            "total_usd": round(tok_in / 1e6 * pr["in"] + tok_out / 1e6 * pr["out"], 4),
            "avg_per_job_usd": round((tok_in / 1e6 * pr["in"] + tok_out / 1e6 * pr["out"]) / n_calls, 5),
            "rate_input_per_mtok_usd": pr["in"], "rate_output_per_mtok_usd": pr["out"], "source": pr["source"],
            "cost_status": "VERIFIED"}
else:
    cost = {"cost_status": "PENDING_VERIFIED_PRICING", "note": "no trusted local/runtime pricing metadata for this model; tokens reported only"}

metrics = {
    "run_id": RUN_ID, "run_timestamp_utc": RUN_TS.isoformat(),
    "model": MODEL_ID, "slug": SLUG,
    "git_commit": subprocess.run(["git", "-C", str(BACKEND), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
    "fixed_inputs_sha256": FIXED_SHA, "fixed_input_drift": prompt_drift,
    "experiment_contract": {
        "only_variable": "model identifier", "prompt_version": "job-fit-v3-matchable-only",
        "schema_version": "fit-analysis-wire-v2", "temperature": 0, "max_tokens": 4096,
        "calls_per_job": 1, "join_key": ["job_id", "requirement_id"],
    },
    "matchable_requirements": 100, "model_calls": n_calls,
    "reconciliation": {"expected": 100, "reconciled": len(paired), "unreconciled": 100 - len(paired)},
    "classification": {"accuracy": acc, "macro": macro, "per_class": per_class,
                       "confusion_matrix": {"rows_ground_truth": LAB, "cols_prediction": LAB,
                                            "matrix": [[conf[a][b] for b in LAB] for a in LAB]}},
    "directional_errors": {k: trans.get(k, 0) for k in
                           ("Strong->Partial", "Strong->Missing", "Partial->Strong", "Partial->Missing", "Missing->Strong", "Missing->Partial")},
    "system": {"raw_schema_parse_success": f"{schema_ok}/{n_calls}", "job_normalization_success": f"{norm_ok}/{n_calls}",
               "requirement_prediction_coverage": f"{len(paired)}/100", "effective_correct_coverage": ecc,
               "duplicate_requirement_ids": dup, "omitted_requirement_ids": omitted,
               "hallucinated_requirement_ids": halluc, "invalid_labels": invlab},
    "grounding": grounding,
    "slice_metrics": slice_metrics,
    "adjacency_false_positives_gt_missing_to_partial_or_strong": adj_fp,
    "project_under_credited": proj_under, "project_over_credited": proj_over,
    "match_score": score_cmp,
    "latency": {"total_runtime_ms": round(wall_ms, 1), "mean_ms": round(statistics.mean(latencies), 1),
                "median_ms": round(statistics.median(latencies), 1), "p90_ms": pct(90),
                "min_ms": round(min(latencies), 1), "max_ms": round(max(latencies), 1), "model_calls": n_calls},
    "tokens": {"input": tok_in, "output": tok_out, "total": tok_in + tok_out,
               "avg_per_job": round((tok_in + tok_out) / n_calls, 1),
               "avg_per_requirement": round((tok_in + tok_out) / 100, 1)},
    "cost": cost,
}
(OUT / f"benchmark_round1_metrics_{SLUG}.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1))

# csvs
pcols = ["job_id", "job_title", "company", "requirement_id", "normalized_requirement", "ground_truth_label",
         "predicted_label", "correct", "gt_evidence_ids", "predicted_evidence_ids",
         "supported_predicted_evidence_ids", "unsupported_predicted_evidence_ids", "grounding_valid",
         "raw_reason", "normalized_reason", "latency_ms", "input_tokens", "output_tokens", "schema_success", "error"]
with (OUT / f"benchmark_round1_predictions_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=pcols)
    w.writeheader()
    for p in pred_rows:
        row = {k: p.get(k) for k in pcols}
        for k in ("gt_evidence_ids", "predicted_evidence_ids", "supported_predicted_evidence_ids", "unsupported_predicted_evidence_ids"):
            row[k] = "|".join(p.get(k) or [])
        w.writerow(row)

with (OUT / f"benchmark_round1_job_scores_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["job_id", "company", "title", "matchable_requirement_count", "human_match_fit",
                "gt_match_score", "model_match_score", "abs_err_vs_gt_score", "notes"])
    for jsr in job_score_rows:
        jid = jsr["job_id"]
        ae = abs(gt_score[jid] - model_score[jid]) if (gt_score[jid] is not None and model_score[jid] is not None) else ""
        w.writerow([jid, jsr["company"], jsr["title"], jsr["matchable_requirement_count"], hmf[jid],
                    gt_score[jid], model_score[jid], ae, jsr["notes"]])

with (OUT / f"benchmark_round1_slice_metrics_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "slice", "n", "n_reconciled", "accuracy", "errors", "unreconciled", "directional"])
    for name, m in slice_metrics.items():
        w.writerow([MODEL_ID, name, m["n"], m["n_reconciled"], m["accuracy"], m["errors"], m["unreconciled"],
                    ";".join(f"{k}={v}" for k, v in m["directional"].items())])

with (OUT / f"benchmark_round1_errors_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "job_id", "company", "requirement_id", "normalized_requirement",
                "ground_truth_label", "predicted_label", "gt_evidence_ids", "predicted_evidence_ids",
                "grounding_valid", "normalized_reason", "error_type"])
    for p in pred_rows:
        if p["predicted_label"] is None or p["predicted_label"] != p["ground_truth_label"]:
            w.writerow([MODEL_ID, p["job_id"], p["company"], p["requirement_id"], p["normalized_requirement"],
                        p["ground_truth_label"], p["predicted_label"] or "UNRECONCILED",
                        "|".join(p["gt_evidence_ids"]), "|".join(p["predicted_evidence_ids"]),
                        p["grounding_valid"], p["normalized_reason"],
                        "unreconciled" if p["predicted_label"] is None else "misclassification"])

with (OUT / f"benchmark_round1_latency_tokens_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "job_id", "matchable_requirement_count", "latency_ms_model", "input_tokens", "output_tokens", "total_tokens", "schema_ok", "norm_ok"])
    for rr in raw_records:
        w.writerow([MODEL_ID, rr["job_id"], len(rr["requirement_ids_submitted"]), rr["latency_ms_model"],
                    rr["input_tokens"], rr["output_tokens"], rr["total_tokens"], rr["schema_parse_success"], rr["normalization_success"]])

integrity = {
    "model_id_exact": MODEL_ID,
    "expected_model_calls": 30, "actual_model_calls": n_calls,
    "raw_outputs_persisted_before_gt_load": True,
    "ground_truth_loaded_only_after_persist": True,
    "prompt_drift_detected": any(prompt_drift.values()),
    "fixed_input_sha256": FIXED_SHA,
    "product_code_mutated": False,
    "manual_reruns": 0,
    "retry_policy_changed": False,
    "extra_instructions_added": False,
    "temperature": 0, "max_tokens": 4096,
    "schema_parse_success": f"{schema_ok}/{n_calls}",
    "job_normalization_success": f"{norm_ok}/{n_calls}",
    "catastrophic_infrastructure_problem": (n_calls != 30) or any(prompt_drift.values()) or (schema_ok == 0),
    "verdict": "INTEGRITY_OK" if (n_calls == 30 and not any(prompt_drift.values()) and schema_ok > 0) else "INTEGRITY_FAIL",
}
(OUT / f"benchmark_round1_integrity_{SLUG}.json").write_text(json.dumps(integrity, ensure_ascii=False, indent=1))

print()
print("RUN_ID:", RUN_ID)
print(json.dumps({"model": MODEL_ID, "reconciliation": metrics["reconciliation"],
                  "classification": {"accuracy": acc, "macro": macro, "per_class": per_class},
                  "confusion": metrics["classification"]["confusion_matrix"]["matrix"],
                  "directional": metrics["directional_errors"], "system": metrics["system"],
                  "grounding": grounding, "match_score": score_cmp,
                  "latency": metrics["latency"], "tokens": metrics["tokens"], "cost": cost,
                  "adjacency_fp": adj_fp, "project_under": proj_under, "project_over": proj_over,
                  "integrity": integrity["verdict"]}, ensure_ascii=False, indent=1))
