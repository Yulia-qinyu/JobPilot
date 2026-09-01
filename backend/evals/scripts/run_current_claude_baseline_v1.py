"""Current Claude Baseline V1 — measure the CURRENT JobPilot semantic matcher as-is.

Runs the production RequirementMatcher (unmodified) over the 100 frozen matchable
requirements from job-match-ground-truth-v2 against the frozen candidate evidence
snapshot. One production Phase-3 semantic call per job (30 calls). Ground Truth
labels are loaded ONLY after all predictions are generated.

NO prompt / model / schema / temperature / normalization / scoring change.
Eval-only helper: imports production services, mutates nothing.

Usage:  python backend/evals/scripts/run_current_claude_baseline_v1.py
"""

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path("/Users/yulia/Documents/JobPilot/backend")
EVALS = BACKEND / "evals"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings                                  # noqa: E402
from app.schemas.fit_analysis import EvidenceSourceRead              # noqa: E402
from app.services.claude_client import ClaudeServiceError, ClaudeStructuredClient  # noqa: E402
from app.services.evidence_catalog import EvidenceCatalog            # noqa: E402
from app.services.fit_analysis_service import (                      # noqa: E402
    FitAnalysisNormalizationError,
    FitAnalysisService,
)
from app.services.match_score import MatchScoreService, NoScorableRequirementsError  # noqa: E402
from app.services.requirement_catalog import RequirementCatalog, RequirementCatalogBuilder, ScoredRequirement  # noqa: E402
from app.services.requirement_matcher import RequirementMatcher      # noqa: E402

IMPORTANCE_HINT = {"Critical": "high", "Important": "medium", "Preferred": "low"}
GT_PATH = EVALS / "job_match_annotation_full_v2_human_verified.json"
DS_PATH = EVALS / "job_match_eval_dataset_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str:
    return subprocess.run(["git", "-C", str(BACKEND), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def git_dirty() -> str:
    out = subprocess.run(["git", "-C", str(BACKEND), "status", "--porcelain"],
                         capture_output=True, text=True).stdout.strip()
    return out or "(clean)"


# --------------------------------------------------------------------------- setup
settings = get_settings()
gt = json.loads(GT_PATH.read_text())
ds = json.loads(DS_PATH.read_text())
ds_title = {j["job_id"]: j["title"] for j in ds["jobs"]}
ds_company = {j["job_id"]: j["company"] for j in ds["jobs"]}

RUN_TS = datetime.now(timezone.utc)
RUN_ID = "current-claude-baseline-v1-" + RUN_TS.strftime("%Y%m%d-%H%M%S")

matcher_src = (BACKEND / "app/services/requirement_matcher.py").read_text()
prompt_hash = hashlib.sha256(matcher_src.encode()).hexdigest()

# frozen candidate evidence snapshot -> production EvidenceCatalog
snap = gt["candidate_evidence_snapshot"]
sources: list[EvidenceSourceRead] = []
for e in snap["evidence_catalog"]:
    st, _, sid = e["evidence_id"].partition(":")
    sources.append(EvidenceSourceRead(source_type=st, source_id=sid,
                                      text=e["text_summary"], context=e["context"]))
evidence = EvidenceCatalog(sources=sources,
                           resume_hash=snap["resume_hash"],
                           experience_bank_hash=snap["experience_bank_hash"])
valid_evidence_ids = {f"{s.source_type}:{s.source_id}" for s in sources}
assert valid_evidence_ids == {e["evidence_id"] for e in snap["evidence_catalog"]}

# frozen matchable requirements grouped by job (predictions input only)
matchable_by_job: dict[str, list[dict]] = {}
gt_label: dict[tuple[str, str], str] = {}
gt_evidence: dict[tuple[str, str], list[str]] = {}
gt_importance: dict[tuple[str, str], str] = {}
for j in gt["jobs"]:
    for r in j["requirements"]:
        if r["requirement_type"] == "matchable" and r["score_included"]:
            matchable_by_job.setdefault(j["job_id"], []).append(r)
            key = (j["job_id"], r["requirement_id"])
            gt_label[key] = r["human_match_label"]
            gt_evidence[key] = list(r["human_evidence_ids"])
            gt_importance[key] = r["importance"]

human_match_fit = {j["job_id"]: j["human_match_fit"] for j in gt["jobs"]}
job_order = [j["job_id"] for j in gt["jobs"]]
total_matchable = sum(len(v) for v in matchable_by_job.values())
assert total_matchable == 100, total_matchable

# production normalizer (SQLite session; _normalize_matches touches no table)
from sqlalchemy import create_engine                                 # noqa: E402
from sqlalchemy.orm import Session                                   # noqa: E402
from sqlalchemy.pool import StaticPool                               # noqa: E402

_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
fit_service = FitAnalysisService(Session(_engine), settings)
score_service = MatchScoreService()

# --------------------------------------------------------------------------- run
raw_records: list[dict] = []
pred_rows: list[dict] = []          # one per matchable requirement
job_score_rows: list[dict] = []
latencies_ms: list[float] = []
model_latency_ms_total = 0.0
tok_in = tok_out = 0
n_calls = 0
schema_ok_calls = 0
norm_ok_calls = 0

wall_start = time.perf_counter()
for jid in job_order:
    rows = matchable_by_job[jid]
    scored = [
        ScoredRequirement(requirement_id=r["requirement_id"], text=r["normalized_requirement"],
                          context=r["source_text"], importance_hint=IMPORTANCE_HINT[r["importance"]],
                          source_kind="v2_matchable")
        for r in rows
    ]
    catalog = RequirementCatalog(requirements=scored, structured_jd_hash="eval-baseline-not-persisted")
    client = ClaudeStructuredClient(settings)
    matcher = RequirementMatcher(client)

    submitted_ids = [s.requirement_id for s in scored]
    req_payload = [{"requirement_id": s.requirement_id, "requirement_text": s.text,
                    "context": s.context, "importance_hint": s.importance_hint,
                    "source_kind": s.source_kind} for s in scored]
    ev_payload = [{"evidence_source_id": f"{s.source_type}:{s.source_id}", "source_type": s.source_type,
                   "text": s.text, "context": s.context} for s in sources]

    t0 = time.perf_counter()
    err = None
    raw_output = None
    normalized = None
    n_calls += 1
    try:
        out = matcher.analyze(catalog, evidence)          # ONE production Phase-3 call
        raw_output = out.model_dump(mode="json")
        schema_ok_calls += 1
        schema_success = True
    except ClaudeServiceError as ex:
        schema_success = False
        err = f"{type(ex).__name__}:{ex.code}:{ex}"
        out = None
    call_ms = (time.perf_counter() - t0) * 1000
    metrics = dict(client.last_call_metrics)
    m_lat = float(metrics.get("elapsed_seconds") or 0.0) * 1000
    model_latency_ms_total += m_lat
    latencies_ms.append(m_lat if m_lat else call_ms)
    ti = metrics.get("input_tokens") or 0
    to = metrics.get("output_tokens") or 0
    tok_in += ti
    tok_out += to

    norm_error = None
    norm_dump = None
    if out is not None:
        try:
            normalized, unsupported_cnt, hard_dg, det_adj = fit_service._normalize_matches(
                out, catalog, evidence)
            norm_ok_calls += 1
            norm_dump = [m.model_dump(mode="json") for m in normalized]
        except FitAnalysisNormalizationError as ex:
            norm_error = str(ex)

    raw_records.append({
        "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
        "requirement_ids_submitted": submitted_ids,
        "requirement_payload": req_payload,
        "evidence_catalog_submitted": ev_payload,
        "model": client.model,
        "request_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_model_output_parsed": raw_output,          # Anthropic structured-output parsed result, pre-normalization
        "normalized_backend_output": norm_dump,
        "latency_ms_model": round(m_lat, 1),
        "latency_ms_walltime": round(call_ms, 1),
        "input_tokens": ti, "output_tokens": to, "total_tokens": ti + to,
        "estimated_cost": "unavailable (no pricing in repo config)",
        "retry_count": "not exposed by Anthropic SDK messages.parse; production uses SDK default retries",
        "schema_parse_success": schema_success,
        "normalization_success": norm_error is None and out is not None,
        "normalization_error": norm_error,
        "error": err,
    })

    # per-requirement predictions
    pred_by_id: dict[str, dict] = {}
    if normalized is not None:
        for m in normalized:
            pred_by_id[m.requirement_id] = m
    for r in rows:
        rid = r["requirement_id"]
        key = (jid, rid)
        m = pred_by_id.get(rid)
        raw_reason = ""
        if raw_output:
            for rm in raw_output["requirement_matches"]:
                if rm["requirement_id"] == rid:
                    raw_reason = rm["reason"]
                    break
        if m is not None:
            pred_label = m.match_status
            pred_ev = [f"{s['source_type']}:{s['source_id']}" for s in m.model_dump(mode="json")["evidence_sources"]]
            supported = [e for e in pred_ev if e in valid_evidence_ids]
            unsupported = [e for e in pred_ev if e not in valid_evidence_ids]
            grounding_valid = (pred_label in ("Strong", "Partial") and len(supported) >= 1) or pred_label == "Missing"
            norm_reason = m.reason
            row_err = ""
        else:
            pred_label = None
            pred_ev = supported = unsupported = []
            grounding_valid = None
            norm_reason = ""
            row_err = err or norm_error or "no prediction"
        pred_rows.append({
            "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
            "requirement_id": rid, "normalized_requirement": r["normalized_requirement"],
            "ground_truth_label": gt_label[key],
            "predicted_label": pred_label,
            "correct": (pred_label == gt_label[key]) if pred_label else None,
            "gt_evidence_ids": gt_evidence[key],
            "predicted_evidence_ids": pred_ev,
            "supported_predicted_evidence_ids": supported,
            "unsupported_predicted_evidence_ids": unsupported,
            "grounding_valid": grounding_valid,
            "raw_reason": raw_reason,
            "normalized_reason": norm_reason,
            "latency_ms": round(m_lat, 1),
            "input_tokens": ti, "output_tokens": to, "total_tokens": ti + to,
            "schema_success": schema_success and norm_error is None,
            "error": row_err,
        })

    # job-level deterministic Match Score (faithful production: model-predicted importance + label)
    baseline_score = None
    score_status = "unavailable"
    if normalized:
        try:
            baseline_score = score_service.score(normalized)
            score_status = "available"
        except NoScorableRequirementsError as ex:
            score_status = f"unavailable:{ex}"
    pj = [p for p in pred_rows if p["job_id"] == jid]
    job_score_rows.append({
        "job_id": jid, "company": ds_company[jid], "title": ds_title[jid],
        "human_match_fit": human_match_fit[jid],
        "baseline_match_score": baseline_score,
        "score_status": score_status,
        "matchable_requirement_count": len(rows),
        "predicted_strong": sum(1 for p in pj if p["predicted_label"] == "Strong"),
        "predicted_partial": sum(1 for p in pj if p["predicted_label"] == "Partial"),
        "predicted_missing": sum(1 for p in pj if p["predicted_label"] == "Missing"),
        "ground_truth_strong": sum(1 for p in pj if p["ground_truth_label"] == "Strong"),
        "ground_truth_partial": sum(1 for p in pj if p["ground_truth_label"] == "Partial"),
        "ground_truth_missing": sum(1 for p in pj if p["ground_truth_label"] == "Missing"),
        "eligibility_summary_reference": "eligibility evaluated separately (deterministic); excluded from this score",
        "notes": (err or norm_error or ""),
    })
    print(f"  {jid:<44} calls={len(rows):>2}  score={baseline_score}  "
          f"tok={ti}+{to}  {round(m_lat)}ms  {'OK' if (raw_output and not norm_error) else 'FAIL:'+str(err or norm_error)}")

wall_ms = (time.perf_counter() - wall_start) * 1000

# --------------------------------------------------------------------------- metrics
LABELS = ["Strong", "Partial", "Missing"]
paired = [p for p in pred_rows if p["predicted_label"] is not None]
n_reconciled = len(paired)
y_true = [p["ground_truth_label"] for p in paired]
y_pred = [p["predicted_label"] for p in paired]

conf = {gtl: {pl: 0 for pl in LABELS} for gtl in LABELS}
for t, pr in zip(y_true, y_pred):
    conf[t][pr] += 1

def prf(lbl):
    tp = conf[lbl][lbl]
    fp = sum(conf[o][lbl] for o in LABELS if o != lbl)
    fn = sum(conf[lbl][o] for o in LABELS if o != lbl)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 4), round(r, 4), round(f, 4), tp, fp, fn

per_class = {lbl: dict(zip(("precision", "recall", "f1", "tp", "fp", "fn"), prf(lbl))) for lbl in LABELS}
accuracy = round(sum(1 for t, pr in zip(y_true, y_pred) if t == pr) / len(paired), 4) if paired else 0.0
macro_p = round(statistics.mean(per_class[l]["precision"] for l in LABELS), 4)
macro_r = round(statistics.mean(per_class[l]["recall"] for l in LABELS), 4)
macro_f1 = round(statistics.mean(per_class[l]["f1"] for l in LABELS), 4)

# grounding
sp = [p for p in paired if p["predicted_label"] in ("Strong", "Partial")]
grounding_rate = round(sum(1 for p in sp if p["supported_predicted_evidence_ids"]) / len(sp), 4) if sp else None
unsupported_match_rate = round(sum(1 for p in sp if p["unsupported_predicted_evidence_ids"]) / len(sp), 4) if sp else None
all_pred_ev = [e for p in paired for e in p["predicted_evidence_ids"]]
evidence_id_validity_rate = round(sum(1 for e in all_pred_ev if e in valid_evidence_ids) / len(all_pred_ev), 4) if all_pred_ev else None
missing_with_evidence = [p for p in paired if p["predicted_label"] == "Missing" and p["predicted_evidence_ids"]]
sp_zero_evidence = [p for p in sp if not p["predicted_evidence_ids"]]

# human-evidence agreement (SECONDARY)
def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 1.0
ev_pairs = [(p["predicted_evidence_ids"], p["gt_evidence_ids"]) for p in sp]
exact_set = round(sum(1 for a, b in ev_pairs if set(a) == set(b)) / len(ev_pairs), 4) if ev_pairs else None
jaccard = round(statistics.mean(jacc(a, b) for a, b in ev_pairs), 4) if ev_pairs else None
atleast1 = round(sum(1 for a, b in ev_pairs if set(a) & set(b)) / len(ev_pairs), 4) if ev_pairs else None

# schema
omitted = sum(1 for p in pred_rows if p["predicted_label"] is None)
raw_ids_all = []
dup_pred = 0
halluc = 0
invalid_lbl = 0
for rr in raw_records:
    ro = rr["raw_model_output_parsed"]
    if not ro:
        continue
    ids = [m["requirement_id"] for m in ro["requirement_matches"]]
    dup_pred += len(ids) - len(set(ids))
    halluc += sum(1 for i in ids if i not in rr["requirement_ids_submitted"])
    invalid_lbl += sum(1 for m in ro["requirement_matches"] if m["match_status"] not in LABELS)

# match score vs human match fit (Spearman primary)
def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0

def pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else 0.0

scored_jobs = [r for r in job_score_rows if r["baseline_match_score"] is not None]
xs = [r["baseline_match_score"] for r in scored_jobs]
ys = [r["human_match_fit"] for r in scored_jobs]
sp_corr = round(spearman(xs, ys), 4) if len(xs) >= 2 else None
pe_corr = round(pearson(xs, ys), 4) if len(xs) >= 2 else None

lat_sorted = sorted(latencies_ms)
def pct(p):
    if not lat_sorted:
        return None
    k = max(0, min(len(lat_sorted) - 1, int(round(p / 100 * (len(lat_sorted) - 1)))))
    return round(lat_sorted[k], 1)

metrics = {
    "run_id": RUN_ID,
    "run_timestamp_utc": RUN_TS.isoformat(),
    "git_commit": git_commit(),
    "git_working_tree": git_dirty(),
    "model": {
        "provider": "anthropic",
        "model": settings.claude_model,
        "temperature": 0,
        "max_tokens": 4096,
        "structured_output": "anthropic messages.parse output_format=FitAnalysisOutput",
        "matcher_prompt_version": RequirementMatcher.PROMPT_VERSION,
        "matcher_schema_version": RequirementMatcher.SCHEMA_VERSION,
        "matcher_source_sha256": prompt_hash,
        "retry_policy": "Anthropic SDK default (max_retries=2); no eval-added retries",
        "timeout": "Anthropic SDK default",
        "prompt_source": "app/services/requirement_matcher.py (unmodified)",
    },
    "frozen_inputs": {
        "ground_truth_v2_sha256": sha(GT_PATH),
        "dataset_v1_json_sha256": sha(DS_PATH),
        "dataset_v1_csv_sha256": sha(EVALS / "job_match_eval_dataset_v1.csv"),
        "candidate_evidence_resume_hash": snap["resume_hash"],
        "candidate_evidence_experience_bank_hash": snap["experience_bank_hash"],
        "candidate_evidence_catalog_version": snap["catalog_version"],
        "candidate_evidence_catalog_size": len(snap["evidence_catalog"]),
    },
    "matchable_requirements": total_matchable,
    "model_calls": n_calls,
    "reconciliation": {
        "expected": total_matchable,
        "reconciled_by_job_id_requirement_id": n_reconciled,
        "unreconciled": total_matchable - n_reconciled,
        "join_key": ["job_id", "requirement_id"],
    },
    "ground_truth_label_distribution": dict(Counter(gt_label.values())),
    "classification": {
        "accuracy": accuracy,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": {"rows_ground_truth": LABELS, "cols_prediction": LABELS,
                             "matrix": [[conf[t][p] for p in LABELS] for t in LABELS]},
    },
    "grounding": {
        "grounding_rate": grounding_rate,
        "unsupported_match_rate": unsupported_match_rate,
        "evidence_id_validity_rate": evidence_id_validity_rate,
        "missing_with_evidence_rate": round(len(missing_with_evidence) / len(paired), 4) if paired else None,
        "matched_with_zero_evidence_rate": round(len(sp_zero_evidence) / len(sp), 4) if sp else None,
        "predicted_strong_partial_rows": len(sp),
    },
    "human_evidence_agreement_secondary": {
        "exact_set_match_rate": exact_set,
        "mean_jaccard": jaccard,
        "at_least_one_overlap_rate": atleast1,
    },
    "schema": {
        "schema_success_rate": round(schema_ok_calls / n_calls, 4),
        "normalization_success_rate": round(norm_ok_calls / n_calls, 4),
        "complete_job_call_success_rate": round(norm_ok_calls / n_calls, 4),
        "omitted_requirements": omitted,
        "duplicate_predictions": dup_pred,
        "hallucinated_requirement_ids": halluc,
        "invalid_labels": invalid_lbl,
        "retry_count": "not exposed by SDK",
    },
    "latency": {
        "total_runtime_ms": round(wall_ms, 1),
        "total_model_latency_ms": round(model_latency_ms_total, 1),
        "mean_ms": round(statistics.mean(latencies_ms), 1) if latencies_ms else None,
        "median_ms": round(statistics.median(latencies_ms), 1) if latencies_ms else None,
        "p90_ms": pct(90),
        "min_ms": round(min(latencies_ms), 1) if latencies_ms else None,
        "max_ms": round(max(latencies_ms), 1) if latencies_ms else None,
        "model_calls": n_calls,
    },
    "tokens": {
        "input": tok_in, "output": tok_out, "total": tok_in + tok_out,
        "avg_per_job": round((tok_in + tok_out) / n_calls, 1),
        "avg_per_requirement": round((tok_in + tok_out) / total_matchable, 1),
    },
    "cost": {
        "total": None, "avg_per_job": None, "currency": "USD",
        "availability": "unavailable — no model pricing present in repo config; web pricing lookup disallowed by task",
    },
    "job_level": {
        "spearman_match_score_vs_human_match_fit": sp_corr,
        "pearson_optional": pe_corr,
        "jobs_scored": len(scored_jobs),
        "match_score_meaning": "verified career-evidence coverage of matchable requirements ONLY; not overall applicant suitability; eligibility separate",
    },
    "determinism": "single run (Baseline V1); temperature=0; no repeats; variance not measured",
}

# --------------------------------------------------------------------------- write
(EVALS / "job_match_baseline_claude_current_v1_raw.json").write_text(
    json.dumps({"run_id": RUN_ID, "model": settings.claude_model, "calls": raw_records}, ensure_ascii=False, indent=1))

(EVALS / "job_match_baseline_claude_current_v1_predictions.json").write_text(
    json.dumps({"run_id": RUN_ID, "join_key": ["job_id", "requirement_id"], "predictions": pred_rows},
               ensure_ascii=False, indent=1))

pcols = ["job_id", "job_title", "company", "requirement_id", "normalized_requirement",
         "ground_truth_label", "predicted_label", "correct", "gt_evidence_ids",
         "predicted_evidence_ids", "supported_predicted_evidence_ids", "unsupported_predicted_evidence_ids",
         "grounding_valid", "raw_reason", "normalized_reason", "latency_ms",
         "input_tokens", "output_tokens", "total_tokens", "schema_success", "error"]
with (EVALS / "job_match_baseline_claude_current_v1_predictions.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=pcols)
    w.writeheader()
    for p in pred_rows:
        row = dict(p)
        for k in ("gt_evidence_ids", "predicted_evidence_ids", "supported_predicted_evidence_ids",
                  "unsupported_predicted_evidence_ids"):
            row[k] = "|".join(row[k])
        w.writerow(row)

jcols = ["job_id", "company", "title", "human_match_fit", "baseline_match_score", "score_status",
         "matchable_requirement_count", "predicted_strong", "predicted_partial", "predicted_missing",
         "ground_truth_strong", "ground_truth_partial", "ground_truth_missing",
         "absolute_rank_difference", "eligibility_summary_reference", "notes"]
# absolute rank difference between baseline_match_score rank and human_match_fit rank
def rank_map(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    rk = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rk[order[k]] = avg
        i = j + 1
    return rk
sj = [r for r in job_score_rows if r["baseline_match_score"] is not None]
r_score = rank_map([r["baseline_match_score"] for r in sj])
r_fit = rank_map([r["human_match_fit"] for r in sj])
rankdiff = {sj[i]["job_id"]: abs(r_score[i] - r_fit[i]) for i in range(len(sj))}
with (EVALS / "job_match_baseline_claude_current_v1_job_scores.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=jcols)
    w.writeheader()
    for r in job_score_rows:
        row = dict(r)
        row["absolute_rank_difference"] = round(rankdiff.get(r["job_id"], ""), 1) if r["job_id"] in rankdiff else ""
        w.writerow(row)

(EVALS / "job_match_baseline_claude_current_v1_metrics.json").write_text(
    json.dumps(metrics, ensure_ascii=False, indent=1))

# errors.csv: every incorrect or unreconciled prediction (bucket assigned in report step)
ecols = ["job_id", "company", "requirement_id", "normalized_requirement", "source_context",
         "ground_truth_label", "predicted_label", "gt_evidence_ids", "predicted_evidence_ids",
         "grounding_valid", "normalized_reason", "error_type"]
with (EVALS / "job_match_baseline_claude_current_v1_errors.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=ecols)
    w.writeheader()
    src_ctx = {}
    for j in gt["jobs"]:
        for r in j["requirements"]:
            src_ctx[(j["job_id"], r["requirement_id"])] = r["source_text"]
    for p in pred_rows:
        if p["predicted_label"] is None or p["predicted_label"] != p["ground_truth_label"]:
            w.writerow({
                "job_id": p["job_id"], "company": p["company"], "requirement_id": p["requirement_id"],
                "normalized_requirement": p["normalized_requirement"],
                "source_context": src_ctx.get((p["job_id"], p["requirement_id"]), ""),
                "ground_truth_label": p["ground_truth_label"], "predicted_label": p["predicted_label"],
                "gt_evidence_ids": "|".join(p["gt_evidence_ids"]),
                "predicted_evidence_ids": "|".join(p["predicted_evidence_ids"]),
                "grounding_valid": p["grounding_valid"], "normalized_reason": p["normalized_reason"],
                "error_type": "unreconciled" if p["predicted_label"] is None else "misclassification",
            })

print()
print("RUN_ID:", RUN_ID)
print(json.dumps({k: metrics[k] for k in ("matchable_requirements", "model_calls", "reconciliation",
                                          "classification", "grounding", "schema", "latency", "tokens",
                                          "job_level")}, ensure_ascii=False, indent=1))
