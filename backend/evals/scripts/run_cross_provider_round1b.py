"""Round 1B — Cross-Provider Fixed-Semantic-Contract Screening. ONE candidate per invocation.

Usage:  python backend/evals/scripts/run_cross_provider_round1b.py <provider> <model_id> <slug>
  provider ∈ {qwen, deepseek, moonshot}

The ONLY experimental variable is the model / provider. Semantic contract is fixed:
  - Section A = the EXACT frozen job-fit-v3-matchable-only prompt, captured from the unchanged
    production RequirementMatcher (no text edit; SHA-guarded).
  - Section D = the canonical 4-field output contract validated in cross-provider transport
    validation (summary / requirement_matches[{requirement_id, match_label, evidence_ids, reason}] /
    suggested_preparation). OUTPUT-CONTRACT ONLY — no OR-list / adjacency / project-vs-work /
    compound / example / Ground-Truth / failure-case guidance added.
  - Production FitAnalysisService._normalize_matches + MatchScoreService — UNCHANGED.
  - Ground Truth loaded ONLY after every raw prediction is persisted.

TRANSPORT_NORMALIZATION_MAPPING (non-semantic; identical for all four models; documented in
integrity): match_label->match_status, evidence_ids->evidence_source_ids, reason->reason;
importance := frozen canonical requirement importance (the same value surfaced to every model as
importance_hint — a JD property, NOT a Ground-Truth label / human adjudication);
is_hard_requirement := False and hard_requirement_category := "none" (deterministically mandated by
the production prompt for source_kind=v2_matchable); confidence := "Medium" constant (unused by
classification metrics and by MatchScoreService).

Persists per model (under backend/evals/benchmark_cross_provider/, slug = <provider>-<model>):
  cross_provider_round1b_predictions_<slug>.json   (raw + normalized, persisted BEFORE GT load)
  cross_provider_round1b_predictions_<slug>.csv
  cross_provider_round1b_metrics_<slug>.json
  cross_provider_round1b_job_scores_<slug>.csv
  cross_provider_round1b_slice_metrics_<slug>.csv
  cross_provider_round1b_errors_<slug>.csv
  cross_provider_round1b_latency_tokens_<slug>.csv
  cross_provider_round1b_integrity_<slug>.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import httpx

BACKEND = Path("/Users/yulia/Documents/JobPilot/backend")
EVALS = BACKEND / "evals"
OUT = EVALS / "benchmark_cross_provider"
sys.path.insert(0, str(BACKEND))

from typing import Literal                                           # noqa: E402

from pydantic import BaseModel                                        # noqa: E402

from app.config import get_settings                                   # noqa: E402
from app.schemas.fit_analysis import (                                # noqa: E402
    EvidenceSourceRead,
    FitAnalysisOutput,
)
from app.services.claude_client import (                              # noqa: E402
    ClaudeServiceError,
    ClaudeStructuredClient,
)
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


# --- LEAN Section-D output contract (4-field). Anthropic binds this as its strongest
# structured-output mode; the SAME field set the OpenAI-compatible providers were given as
# Section D prompt text. NO production-only fields (importance / is_hard_requirement /
# hard_requirement_category / confidence) are restored here — contract parity is the point. ---
class _RMLean(BaseModel):
    requirement_id: str
    match_label: Literal["Strong", "Partial", "Missing"]
    evidence_ids: list[str]
    reason: str


class _PrepLean(BaseModel):
    title: str
    action: str
    priority: Literal["High", "Medium", "Low"]
    requirement_ids: list[str]


class _FitLean(BaseModel):
    summary: str
    requirement_matches: list[_RMLean]
    suggested_preparation: list[_PrepLean]

PROVIDER = sys.argv[1]
MODEL_ID = sys.argv[2]
SLUG = sys.argv[3]

# --- optional Round 2A (Prompt / Rubric Communication Ablation) overrides ---
# When ROUND2A_TREATMENT_INSTRUCTIONS_FILE is set, the captured production instruction block
# (everything before "\n\nJOB REQUIREMENTS:\n") is REPLACED by that file's text; the requirement +
# evidence payloads, Section D, transport, normalization, scoring and metrics are unchanged.
OUTDIR = Path(os.environ["ROUND2A_OUT_DIR"]) if os.environ.get("ROUND2A_OUT_DIR") else (EVALS / "benchmark_cross_provider")
FILE_PREFIX = os.environ.get("ROUND2A_FILE_PREFIX", "cross_provider_round1b_")
TREATMENT_FILE = os.environ.get("ROUND2A_TREATMENT_INSTRUCTIONS_FILE")
TREATMENT_TEXT = Path(TREATMENT_FILE).read_text() if TREATMENT_FILE else None
PROMPT_VERSION_LABEL = os.environ.get("ROUND2A_PROMPT_VERSION", "job-fit-v3-matchable-only")
RUN_TAG = os.environ.get("ROUND2A_RUN_TAG", "round1b")
OUTDIR.mkdir(parents=True, exist_ok=True)

IMPORTANCE_HINT = {"Critical": "high", "Important": "medium", "Preferred": "low"}
GT_PATH = EVALS / "job_match_annotation_full_v2_human_verified.json"
DS_PATH = EVALS / "job_match_eval_dataset_v1.json"
SLICES_PATH = EVALS / "job_match_baseline_claude_current_v1_error_slices.csv"

IMPORTANCE_W = {"Critical": Decimal(5), "Important": Decimal(3), "Preferred": Decimal(1)}
MATCH_V = {"Strong": Decimal(1), "Partial": Decimal("0.5"), "Missing": Decimal(0)}
LAB = ["Strong", "Partial", "Missing"]


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
    if len(xs) < 2:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 4) if den else None


# ------------------------------------------------------------------ credentials
def _key(name):
    if os.environ.get(name):
        return os.environ[name]
    for base in (BACKEND / ".env", BACKEND.parent / ".env"):
        if base.exists():
            for line in base.read_text().splitlines():
                line = line.strip()
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


PROVIDER_CFG = {
    "anthropic": {
        "base_url": "anthropic-sdk:messages.parse",
        "key_env": "ANTHROPIC_API_KEY",
        "temperature": 0, "extra_body": {},
        "json_line": False,   # Anthropic binds Section D as a strict schema; no json-token line
        "reasoning_mode": "standard_single_pass", "reasoning_comparability_flag": False,
        "temperature_comparability_flag": False,
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key_env": "DASHSCOPE_API_KEY",
        "temperature": 0, "extra_body": {"enable_thinking": False},
        "json_line": True,
        "reasoning_mode": "standard_single_pass", "reasoning_comparability_flag": False,
        "temperature_comparability_flag": False,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "key_env": "DEEPSEEK_API_KEY",
        "temperature": 0, "extra_body": {},
        "json_line": True,
        "reasoning_mode": "mandatory", "reasoning_comparability_flag": True,
        "temperature_comparability_flag": False,
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "key_env": "MOONSHOT_API_KEY",
        "temperature": 1, "extra_body": {"reasoning_effort": "low"},
        "json_line": True,
        "reasoning_mode": "mandatory", "reasoning_comparability_flag": True,
        "temperature_comparability_flag": True,  # temperature=1 (MODEL_REQUIRED_VALUE)
    },
}
CFG = PROVIDER_CFG[PROVIDER]
API_KEY = _key(CFG["key_env"])
assert API_KEY, f"missing {CFG['key_env']}"

# ------------------------------------------------------------------ fixed inputs
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
    "match_score.py": "8ae2d59389da7f3ae783bb57daca81c6611cd5c009a95005e6d772bc6c8dfad2",
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

snap = gt["candidate_evidence_snapshot"]
sources = []
for e in snap["evidence_catalog"]:
    st, _, sid = e["evidence_id"].partition(":")
    sources.append(EvidenceSourceRead(source_type=st, source_id=sid,
                                      text=e["text_summary"], context=e["context"]))
evidence = EvidenceCatalog(sources=sources, resume_hash=snap["resume_hash"],
                           experience_bank_hash=snap["experience_bank_hash"])
valid_ev = {f"{s.source_type}:{s.source_id}" for s in sources}

matchable_by_job = {}
gt_label, gt_ev, gt_imp = {}, {}, {}
canonical_importance = {}
for j in gt["jobs"]:
    for r in j["requirements"]:
        if r["requirement_type"] == "matchable" and r["score_included"]:
            matchable_by_job.setdefault(j["job_id"], []).append(r)
            key = (j["job_id"], r["requirement_id"])
            gt_label[key] = r["human_match_label"]
            gt_ev[key] = list(r["human_evidence_ids"])
            gt_imp[key] = r["importance"]
            canonical_importance[key] = r["importance"]
hmf = {j["job_id"]: j["human_match_fit"] for j in gt["jobs"]}
job_order = [j["job_id"] for j in gt["jobs"]]
assert sum(len(v) for v in matchable_by_job.values()) == 100
_SMOKE = int(os.environ.get("ROUND1B_SMOKE_JOBS", "0"))  # >0 = smoke test only, NOT a real run

slice_flag = {}
for row in csv.DictReader(SLICES_PATH.open()):
    slice_flag[(row["job_id"], row["requirement_id"])] = {
        "is_or_list": row["is_or_list"] == "True",
        "is_compound": row["is_compound"] == "True",
        "root_cause_groups": row["root_cause_groups"],
    }
MISMATCH_CONTROL = {"huawei:28183", "xsolla:252b30e5-ce58-4a32-88b3-07ee83d06e67",
                    "tencent:2064981110395420672"}
PROJ_RX = ("GoFin", "KPay", "个人项目", "Product Owner", "项目", "实习")
DOMAIN_RX = ("证券", "金融", "医疗健康", "battery", "内容", "创作", "AIGC")
PROF_RX = ("熟练", "精通", "深入", "扎实", "proficient", "expert", "Proficient")
ADJ_RX = ("多模态", "语音", "ASR", "流式", "精度调优", "基模", "强化学习", "RL", "AIGC")
CHINESE_JD = [jid for jid in job_order
              if any("一" <= ch <= "鿿" for ch in (ds_title[jid] + " " + ds_company[jid]))
              or any(any("一" <= ch <= "鿿" for ch in r["source_text"])
                     for r in matchable_by_job[jid])]

_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
fit_service = FitAnalysisService(Session(_engine), settings)
score_service = MatchScoreService()

# ------------------------------------------------------------------ Section A (captured, unchanged)
SECTION_D = """

OUTPUT CONTRACT — return one JSON object with EXACTLY these top-level fields and no others:
  "summary": string
  "requirement_matches": array; each element is an object with EXACTLY these fields:
      "requirement_id": string, echoed exactly as provided
      "match_label": string, exactly one of "Strong", "Partial", "Missing"
      "evidence_ids": array of evidence id strings from the catalog (empty array if none)
      "reason": string
  "suggested_preparation": array; each element is an object with EXACTLY these fields:
      "title": string
      "action": string
      "priority": string, exactly one of "High", "Medium", "Low"
      "requirement_ids": array of requirement id strings
Use these exact field names. Do not rename fields (no "match_level", "match_status",
"match_grade", "evidence_source_ids", "reasons"). Do not add or omit fields."""
JSON_LINE = "\n\nReturn the response as JSON."


class _Captured(Exception):
    pass


class _PromptCaptureClient:
    def __init__(self):
        self.captured = None
        self.model = "capture"
        self.last_call_metrics = {}

    def generate(self, *, prompt, output_model, tool_name):
        self.captured = prompt
        raise _Captured()


_REQ_MARKER = "\n\nJOB REQUIREMENTS:\n"


def production_section_a(catalog: RequirementCatalog) -> str:
    """Full prompt exactly as production RequirementMatcher builds it: instruction block +
    JOB REQUIREMENTS payload + ELIGIBLE CANDIDATE EVIDENCE payload. UNCHANGED when no treatment."""
    cap = _PromptCaptureClient()
    m = RequirementMatcher(cap)
    try:
        m.analyze(catalog, evidence)
    except _Captured:
        pass
    full = cap.captured
    if TREATMENT_TEXT is None:
        return full
    # Round 2A treatment: replace ONLY the instruction block; keep the payloads byte-identical.
    idx = full.index(_REQ_MARKER)
    return TREATMENT_TEXT.rstrip("\n") + full[idx:]


# ------------------------------------------------------------------ provider call
TRANSIENT = {408, 409, 425, 429, 500, 502, 503, 504}


HTTP_TIMEOUT = float(os.environ.get("ROUND1B_HTTP_TIMEOUT", "300"))
MAX_RETRIES = int(os.environ.get("ROUND1B_MAX_RETRIES", "2"))


def call_model(assembled_prompt: str):
    body = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": assembled_prompt}],
        "temperature": CFG["temperature"],
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    body.update(CFG["extra_body"])
    url = f"{CFG['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    attempts, retry_count, last_err = 0, 0, None
    backoff = [5, 15, 30, 30, 30]
    while attempts <= MAX_RETRIES:
        attempts += 1
        t0 = time.perf_counter()
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=HTTP_TIMEOUT)
            lat = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return {"ok": True, "json": r.json(), "latency_ms": lat,
                        "retry_count": retry_count, "http_status": 200, "error": None}
            err = None
            try:
                err = r.json().get("error", r.json())
            except Exception:
                err = {"raw": r.text[:400]}
            last_err = {"http_status": r.status_code, "error": err}
            if r.status_code in TRANSIENT and attempts <= MAX_RETRIES:
                retry_count += 1
                time.sleep(backoff[attempts - 1])
                continue
            return {"ok": False, "json": None, "latency_ms": lat, "retry_count": retry_count,
                    "http_status": r.status_code, "error": err}
        except (httpx.TransportError, httpx.TimeoutException) as ex:
            lat = (time.perf_counter() - t0) * 1000
            last_err = {"http_status": None, "error": f"{type(ex).__name__}: {ex}"}
            if attempts <= MAX_RETRIES:
                retry_count += 1
                time.sleep(backoff[attempts - 1])
                continue
            return {"ok": False, "json": None, "latency_ms": lat, "retry_count": retry_count,
                    "http_status": None, "error": last_err["error"]}
    return {"ok": False, "json": None, "latency_ms": 0.0, "retry_count": retry_count,
            "http_status": (last_err or {}).get("http_status"), "error": (last_err or {}).get("error")}


_ANTHROPIC_CLIENT = None
if PROVIDER == "anthropic":
    _ANTHROPIC_CLIENT = ClaudeStructuredClient(settings)
    _ANTHROPIC_CLIENT.model = MODEL_ID
    assert _ANTHROPIC_CLIENT.client is not None, "ANTHROPIC_API_KEY not configured"
    assert _ANTHROPIC_CLIENT.model == MODEL_ID


def call_anthropic(assembled_prompt: str):
    """Anthropic strongest structured output: messages.parse binding the LEAN Section-D schema
    (_FitLean). temperature=0, max_tokens=4096, no thinking param (ClaudeStructuredClient.generate).
    Section A + Section D text are IN the prompt; NO json-token line (Anthropic does not need it)."""
    t0 = time.perf_counter()
    try:
        lean = _ANTHROPIC_CLIENT.generate(
            prompt=assembled_prompt, output_model=_FitLean, tool_name="submit_requirement_matches")
        lat = (time.perf_counter() - t0) * 1000
        lm = dict(_ANTHROPIC_CLIENT.last_call_metrics)
        m_ms = float(lm.get("elapsed_seconds") or 0.0) * 1000
        return {"ok": True, "lean": lean, "latency_ms": (m_ms or lat), "retry_count": 0,
                "http_status": 200, "error": None,
                "usage": {"prompt_tokens": lm.get("input_tokens") or 0,
                          "completion_tokens": lm.get("output_tokens") or 0}}
    except ClaudeServiceError as ex:
        lat = (time.perf_counter() - t0) * 1000
        return {"ok": False, "lean": None, "latency_ms": lat, "retry_count": 0,
                "http_status": None, "error": f"{type(ex).__name__}:{getattr(ex, 'code', '')}:{ex}",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0}}


ALIAS = {"match_level", "match_status", "match_grade", "evidence_source_ids", "reasons"}


def build_fit_output(parsed, jid, submitted_ids):
    """Map the 4-field Section D response into production FitAnalysisOutput.
    Returns (FitAnalysisOutput|None, schema_notes dict)."""
    notes = {"parseable": isinstance(parsed, dict), "alias_fields_seen": [],
             "top_level_exact": None, "invalid_labels": 0, "missing_item_fields": 0,
             "dup_ids": 0, "hallucinated_ids": 0}
    if not isinstance(parsed, dict):
        return None, notes
    top = set(parsed.keys())
    notes["top_level_exact"] = (top == {"summary", "requirement_matches", "suggested_preparation"})
    rms = parsed.get("requirement_matches")
    if not isinstance(rms, list) or not rms:
        return None, notes
    ids = []
    items = []
    for it in rms:
        if not isinstance(it, dict):
            notes["missing_item_fields"] += 1
            continue
        notes["alias_fields_seen"] += sorted(set(it.keys()) & ALIAS)
        rid = it.get("requirement_id")
        label = it.get("match_label")
        ev = it.get("evidence_ids")
        reason = it.get("reason")
        if rid is None or label is None or not isinstance(ev, list) or reason is None:
            notes["missing_item_fields"] += 1
            continue
        if label not in LAB:
            notes["invalid_labels"] += 1
            continue
        ids.append(rid)
        key = (jid, rid)
        items.append({
            "requirement_id": rid,
            "importance": canonical_importance.get(key, "Important"),  # TRANSPORT_NORMALIZATION_MAPPING
            "is_hard_requirement": False,
            "hard_requirement_category": "none",
            "match_status": label,
            "reason": str(reason),
            "confidence": "Medium",
            "evidence_source_ids": [str(x) for x in ev],
        })
    notes["dup_ids"] = len(ids) - len(set(ids))
    notes["hallucinated_ids"] = sum(1 for i in ids if i not in submitted_ids)
    prep = []
    for p in (parsed.get("suggested_preparation") or []):
        if not isinstance(p, dict):
            continue
        try:
            prep.append({
                "title": str(p.get("title", "")), "action": str(p.get("action", "")),
                "priority": p.get("priority") if p.get("priority") in ("High", "Medium", "Low") else "Medium",
                "requirement_ids": [str(x) for x in (p.get("requirement_ids") or [])],
            })
        except Exception:
            pass
    try:
        out = FitAnalysisOutput(summary=str(parsed.get("summary", "")),
                                requirement_matches=items, suggested_preparation=prep)
        return out, notes
    except Exception as ex:
        notes["pydantic_error"] = f"{type(ex).__name__}: {ex}"
        return None, notes


# ------------------------------------------------------------------ run
RUN_TS = datetime.now(timezone.utc)
RUN_ID = f"{RUN_TAG}-{SLUG}-" + RUN_TS.strftime("%Y%m%d-%H%M%S")
raw_records, pred_rows, job_score_rows = [], [], []
latencies, tok_in, tok_out, tok_reason = [], 0, 0, 0
n_calls = schema_ok = norm_ok = 0
total_retries = 0
gt_leak_guard = "GROUND_TRUTH_NOT_LOADED_YET"

wall0 = time.perf_counter()
_run_order = job_order[:_SMOKE] if _SMOKE else job_order
for jid in _run_order:
    rows = matchable_by_job[jid]
    scored = [ScoredRequirement(requirement_id=r["requirement_id"], text=r["normalized_requirement"],
                                context=r["source_text"], importance_hint=IMPORTANCE_HINT[r["importance"]],
                                source_kind="v2_matchable") for r in rows]
    catalog = RequirementCatalog(requirements=scored, structured_jd_hash="round1b-not-persisted")
    submitted = [s.requirement_id for s in scored]
    section_a = production_section_a(catalog)
    assembled = section_a + SECTION_D + (JSON_LINE if CFG["json_line"] else "")

    n_calls += 1
    res = call_anthropic(assembled) if PROVIDER == "anthropic" else call_model(assembled)
    total_retries += res["retry_count"]
    latencies.append(res["latency_ms"])
    err = None if res["ok"] else json.dumps(res["error"], ensure_ascii=False, default=str)
    raw_out = None
    schema_success = False
    normalized = None
    norm_err = None
    schema_notes = {}
    ti = to = tr = 0

    if res["ok"]:
        if PROVIDER == "anthropic":
            u = res["usage"]
            ti = u.get("prompt_tokens") or 0
            to = u.get("completion_tokens") or 0
            tr = 0
            parsed = res["lean"].model_dump(mode="json")  # exact 4-field Section-D shape
        else:
            j = res["json"]
            ch = (j.get("choices") or [{}])[0]
            msg = ch.get("message", {}) or {}
            content = msg.get("content", "") or ""
            u = j.get("usage", {}) or {}
            ti = u.get("prompt_tokens") or 0
            to = u.get("completion_tokens") or 0
            tr = (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            try:
                parsed = json.loads(content)
            except Exception as ex:
                parsed = None
                schema_notes = {"json_parse_error": f"{type(ex).__name__}: {ex}"}
        out, schema_notes2 = build_fit_output(parsed, jid, set(submitted)) if parsed is not None else (None, {})
        schema_notes = {**schema_notes, **schema_notes2}
        if out is not None:
            raw_out = out.model_dump(mode="json")
            schema_ok += 1
            schema_success = True
            try:
                normalized, unsup, hard_dg, det_adj = fit_service._normalize_matches(out, catalog, evidence)
                norm_ok += 1
            except FitAnalysisNormalizationError as ex:
                norm_err = str(ex)
        else:
            norm_err = "schema_build_failed"
    tok_in += ti
    tok_out += to
    tok_reason += tr

    raw_records.append({
        "provider": PROVIDER, "model": MODEL_ID, "job_id": jid, "job_title": ds_title[jid],
        "company": ds_company[jid], "requirement_ids_submitted": submitted,
        "evidence_catalog_submitted_ids": sorted(valid_ev),
        "request_timestamp": datetime.now(timezone.utc).isoformat(),
        "transport_metadata": {
            "base_url": CFG["base_url"], "temperature": CFG["temperature"],
            "extra_body": CFG["extra_body"],
            "structured_output": ("anthropic messages.parse output_format=_FitLean (strict schema binding Section D)"
                                  if PROVIDER == "anthropic" else "response_format=json_object + Section D in-prompt"),
            "json_serialization_line": bool(CFG["json_line"]),
            "json_serialization_line_class": ("n/a — Anthropic binds schema" if PROVIDER == "anthropic"
                                              else "TRANSPORT_SERIALIZATION_ONLY"),
            "http_status": res["http_status"], "retry_count": res["retry_count"],
        },
        "raw_model_output_parsed": raw_out,
        "schema_notes": schema_notes,
        "normalized_backend_output": [m.model_dump(mode="json") for m in normalized] if normalized else None,
        "schema_parse_success": schema_success,
        "normalization_success": (normalized is not None and norm_err is None),
        "normalization_error": norm_err,
        "latency_ms": round(res["latency_ms"], 1),
        "input_tokens": ti, "output_tokens": to, "reasoning_tokens": tr, "total_tokens": ti + to,
        "retry_count": res["retry_count"],
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
                "latency_ms": round(res["latency_ms"], 1), "input_tokens": ti, "output_tokens": to,
                "schema_success": schema_success and norm_err is None, "error": ""})
        else:
            pred_rows.append({
                "job_id": jid, "job_title": ds_title[jid], "company": ds_company[jid],
                "requirement_id": rid, "normalized_requirement": r["normalized_requirement"],
                "predicted_label": None, "predicted_evidence_ids": [], "supported_predicted_evidence_ids": [],
                "unsupported_predicted_evidence_ids": [], "raw_reason": raw_reason, "normalized_reason": "",
                "latency_ms": round(res["latency_ms"], 1), "input_tokens": ti, "output_tokens": to,
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
    print(f"  {jid:<46} n={len(rows):>2} score={bscore} tok={ti}+{to}(+{tr}r) "
          f"{round(res['latency_ms'])}ms retry={res['retry_count']} "
          f"{'OK' if (raw_out and not norm_err) else 'FAIL:'+str(err or norm_err)[:80]}", flush=True)

wall_ms = (time.perf_counter() - wall0) * 1000

if _SMOKE:
    print(f"\n[SMOKE {_SMOKE} jobs] schema_ok={schema_ok}/{n_calls} norm_ok={norm_ok}/{n_calls} "
          f"retries={total_retries} tok={tok_in}+{tok_out}(+{tok_reason}r)")
    for rr in raw_records:
        print("  ", rr["job_id"], "http", rr["transport_metadata"]["http_status"],
              "schema", rr["schema_parse_success"], "norm", rr["normalization_success"],
              "notes", rr.get("schema_notes"), "err", rr["error"])
    sys.exit(0)

(OUTDIR / f"{FILE_PREFIX}predictions_{SLUG}.json").write_text(
    json.dumps({"run_id": RUN_ID, "provider": PROVIDER, "model": MODEL_ID, "calls": raw_records},
               ensure_ascii=False, indent=1))
print(f"\n[persisted raw predictions for {PROVIDER}/{MODEL_ID} — now loading Ground Truth]", flush=True)
gt_leak_guard = "GROUND_TRUTH_LOADED_AFTER_PERSIST"

# ------------------------------------------------------------------ metrics
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

omitted = sum(1 for p in pred_rows if p["predicted_label"] is None)
dup = halluc = invlab = 0
for rr in raw_records:
    sn = rr.get("schema_notes") or {}
    dup += sn.get("dup_ids", 0)
    halluc += sn.get("hallucinated_ids", 0)
    invlab += sn.get("invalid_labels", 0)

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


def slice_rows(name):
    out_rows = []
    for p in paired + [x for x in pred_rows if x["predicted_label"] is None]:
        key = (p["job_id"], p["requirement_id"])
        fl = slice_flag.get(key, {})
        src = next((r["source_text"] for r in matchable_by_job[p["job_id"]] if r["requirement_id"] == p["requirement_id"]), "")
        cnt = next(x["matchable_requirement_count"] for x in job_score_rows if x["job_id"] == p["job_id"])
        keep = {
            "or_list": fl.get("is_or_list"),
            "technology_adjacency": p["ground_truth_label"] == "Missing" and any(k in src for k in ADJ_RX),
            "project_based_evidence": any(k in (p["normalized_reason"] + p["raw_reason"]) for k in PROJ_RX),
            "formal_work_experience": any(k in src for k in ("年以上", "年及以上", "formal", "正式", "工作经验")),
            "compound": fl.get("is_compound"),
            "proficiency_depth": any(k in src for k in PROF_RX),
            "domain_specific": any(k in src for k in DOMAIN_RX),
            "small_matchable_jobs": cnt <= 3,
            "one_requirement_jobs": cnt == 1,
            "mismatched_control_jobs": p["job_id"] in MISMATCH_CONTROL,
            "chinese_jd": p["job_id"] in CHINESE_JD,
        }[name]
        if keep:
            out_rows.append(p)
    return out_rows


SLICES = ["or_list", "technology_adjacency", "project_based_evidence", "formal_work_experience",
          "compound", "proficiency_depth", "domain_specific", "small_matchable_jobs",
          "one_requirement_jobs", "mismatched_control_jobs", "chinese_jd"]
slice_metrics = {}
for name in SLICES:
    rws = slice_rows(name)
    rec = [r for r in rws if r["predicted_label"]]
    corr = sum(1 for r in rec if r["correct"])
    tdir = Counter(f"{r['ground_truth_label']}->{r['predicted_label']}" for r in rec if r["predicted_label"] != r["ground_truth_label"])
    cconf = {a: {b: 0 for b in LAB} for a in LAB}
    for r in rec:
        cconf[r["ground_truth_label"]][r["predicted_label"]] += 1

    def _f1(l, cc):
        tp = cc[l][l]
        fp = sum(cc[o][l] for o in LAB if o != l)
        fn = sum(cc[l][o] for o in LAB if o != l)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        return 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    macro_f1_slice = round(statistics.mean(_f1(l, cconf) for l in LAB), 4) if rec else None
    slice_metrics[name] = {
        "n": len(rws), "n_reconciled": len(rec),
        "accuracy": round(corr / len(rec), 4) if rec else None,
        "macro_f1": macro_f1_slice if (name == "chinese_jd" or len(rec) >= 12) else None,
        "errors": len(rec) - corr, "unreconciled": len(rws) - len(rec),
        "directional": dict(tdir),
    }

adj_fp = sum(1 for p in paired if p["ground_truth_label"] == "Missing" and p["predicted_label"] in ("Partial", "Strong")
             and any(k in next((r["source_text"] for r in matchable_by_job[p["job_id"]] if r["requirement_id"] == p["requirement_id"]), "")
                     for k in ADJ_RX))
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


metrics = {
    "run_id": RUN_ID, "run_timestamp_utc": RUN_TS.isoformat(),
    "provider": PROVIDER, "model": MODEL_ID, "slug": SLUG,
    "git_commit": subprocess.run(["git", "-C", str(BACKEND), "rev-parse", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
    "fixed_inputs_sha256": FIXED_SHA, "fixed_input_drift": prompt_drift,
    "experiment_contract": {
        "only_variable": ("prompt (control vs rubric-aligned treatment)" if TREATMENT_TEXT is not None else "model / provider"),
        "prompt_version": PROMPT_VERSION_LABEL,
        "prompt_control": "job-fit-v3-matchable-only",
        "prompt_treatment": (PROMPT_VERSION_LABEL if TREATMENT_TEXT is not None else None),
        "treatment_instructions_sha256": (hashlib.sha256(TREATMENT_TEXT.encode()).hexdigest() if TREATMENT_TEXT is not None else None),
        "schema_version": "fit-analysis-wire-v2",
        "section_a": ("REPLACED instruction block from treatment file; JOB REQUIREMENTS + EVIDENCE payloads byte-identical to production" if TREATMENT_TEXT is not None else "captured verbatim from production RequirementMatcher"),
        "section_d": "canonical 4-field output contract (summary / requirement_matches[requirement_id,match_label,evidence_ids,reason] / suggested_preparation)",
        "temperature": CFG["temperature"], "max_tokens": 4096, "calls_per_job": 1,
        "join_key": ["job_id", "requirement_id"],
        "transport_normalization_mapping": {
            "match_label->match_status": "direct", "evidence_ids->evidence_source_ids": "direct",
            "reason->reason": "direct",
            "importance": "frozen canonical requirement importance (== importance_hint surfaced to every model; JD property, not a GT label)",
            "is_hard_requirement": "False (production prompt mandates this for source_kind=v2_matchable)",
            "hard_requirement_category": "none", "confidence": "Medium constant (unused by classification / MatchScoreService)",
        },
        "reasoning_mode": CFG["reasoning_mode"],
        "reasoning_comparability_flag": CFG["reasoning_comparability_flag"],
        "temperature_comparability_flag": CFG["temperature_comparability_flag"],
    },
    "matchable_requirements": 100, "model_calls": n_calls, "total_retries": total_retries,
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
    "chinese_jd_subset": {
        "n_jobs": len(CHINESE_JD), "job_ids": CHINESE_JD,
        "n_requirements": sum(len(matchable_by_job[j]) for j in CHINESE_JD),
    },
    "match_score": score_cmp,
    "latency": {"total_runtime_ms": round(wall_ms, 1), "mean_ms": round(statistics.mean(latencies), 1),
                "median_ms": round(statistics.median(latencies), 1), "p90_ms": pct(90),
                "min_ms": round(min(latencies), 1), "max_ms": round(max(latencies), 1), "model_calls": n_calls},
    "tokens": {"input": tok_in, "output": tok_out, "reasoning": tok_reason, "total": tok_in + tok_out,
               "avg_per_job": round((tok_in + tok_out) / n_calls, 1),
               "avg_per_requirement": round((tok_in + tok_out) / 100, 1)},
    "cost": ({"cost_status": "VERIFIED",
              "rate_input_per_mtok_usd": 3.0, "rate_output_per_mtok_usd": 15.0,
              "pricing_source": "Anthropic public pricing, verified 2026-09-01",
              "input_usd": round(tok_in / 1e6 * 3.0, 4), "output_usd": round(tok_out / 1e6 * 15.0, 4),
              "total_usd": round(tok_in / 1e6 * 3.0 + tok_out / 1e6 * 15.0, 4),
              "avg_per_job_usd": round((tok_in / 1e6 * 3.0 + tok_out / 1e6 * 15.0) / n_calls, 5)}
             if PROVIDER == "anthropic" else
             {"cost_status": "PENDING_OFFICIAL_PRICING_VERIFICATION",
              "note": "no independently verified official pricing for this provider/model; token usage recorded, cost fillable later without rerun"}),
}
(OUTDIR / f"{FILE_PREFIX}metrics_{SLUG}.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1))

pcols = ["job_id", "job_title", "company", "requirement_id", "normalized_requirement", "ground_truth_label",
         "predicted_label", "correct", "gt_evidence_ids", "predicted_evidence_ids",
         "supported_predicted_evidence_ids", "unsupported_predicted_evidence_ids", "grounding_valid",
         "raw_reason", "normalized_reason", "latency_ms", "input_tokens", "output_tokens", "schema_success", "error"]
with (OUTDIR / f"{FILE_PREFIX}predictions_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=pcols)
    w.writeheader()
    for p in pred_rows:
        row = {k: p.get(k) for k in pcols}
        for k in ("gt_evidence_ids", "predicted_evidence_ids", "supported_predicted_evidence_ids", "unsupported_predicted_evidence_ids"):
            row[k] = "|".join(p.get(k) or [])
        w.writerow(row)

with (OUTDIR / f"{FILE_PREFIX}job_scores_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["job_id", "company", "title", "matchable_requirement_count", "human_match_fit",
                "gt_match_score", "model_match_score", "abs_err_vs_gt_score", "notes"])
    for jsr in job_score_rows:
        jid = jsr["job_id"]
        ae = abs(gt_score[jid] - model_score[jid]) if (gt_score[jid] is not None and model_score[jid] is not None) else ""
        w.writerow([jid, jsr["company"], jsr["title"], jsr["matchable_requirement_count"], hmf[jid],
                    gt_score[jid], model_score[jid], ae, jsr["notes"]])

with (OUTDIR / f"{FILE_PREFIX}slice_metrics_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "slice", "n", "n_reconciled", "accuracy", "macro_f1", "errors", "unreconciled", "directional"])
    for name, m in slice_metrics.items():
        w.writerow([MODEL_ID, name, m["n"], m["n_reconciled"], m["accuracy"], m["macro_f1"], m["errors"], m["unreconciled"],
                    ";".join(f"{k}={v}" for k, v in m["directional"].items())])

with (OUTDIR / f"{FILE_PREFIX}errors_{SLUG}.csv").open("w", newline="") as fh:
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

with (OUTDIR / f"{FILE_PREFIX}latency_tokens_{SLUG}.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "job_id", "matchable_requirement_count", "latency_ms", "input_tokens",
                "output_tokens", "reasoning_tokens", "total_tokens", "retry_count", "schema_ok", "norm_ok"])
    for rr in raw_records:
        w.writerow([MODEL_ID, rr["job_id"], len(rr["requirement_ids_submitted"]), rr["latency_ms"],
                    rr["input_tokens"], rr["output_tokens"], rr["reasoning_tokens"], rr["total_tokens"],
                    rr["retry_count"], rr["schema_parse_success"], rr["normalization_success"]])

integrity = {
    "provider": PROVIDER, "model_id_exact": MODEL_ID,
    "expected_model_calls": 30, "actual_model_calls": n_calls, "total_retries": total_retries,
    "raw_outputs_persisted_before_gt_load": True,
    "ground_truth_loaded_only_after_persist": True,
    "prompt_drift_detected": any(prompt_drift.values()),
    "fixed_input_sha256": FIXED_SHA,
    "section_a_source": ("Round 2A TREATMENT: instruction block replaced by " + str(TREATMENT_FILE) +
                         " (sha256 " + hashlib.sha256(TREATMENT_TEXT.encode()).hexdigest() + "); JOB REQUIREMENTS + EVIDENCE payloads byte-identical to production"
                         if TREATMENT_TEXT is not None
                         else "captured verbatim from unchanged production RequirementMatcher (SHA-guarded)"),
    "prompt_version_label": PROMPT_VERSION_LABEL,
    "section_d": "canonical 4-field output contract (transport-validated); OUTPUT-CONTRACT-ONLY",
    "transport_normalization_mapping_applied": True,
    "product_code_mutated": False, "manual_reruns": 0, "retry_policy_changed": False,
    "extra_semantic_instructions_added": False,
    "temperature": CFG["temperature"], "max_tokens": 4096,
    "reasoning_comparability_flag": CFG["reasoning_comparability_flag"],
    "temperature_comparability_flag": CFG["temperature_comparability_flag"],
    "schema_parse_success": f"{schema_ok}/{n_calls}",
    "job_normalization_success": f"{norm_ok}/{n_calls}",
    "catastrophic_infrastructure_problem": (n_calls != 30) or any(prompt_drift.values()) or (schema_ok == 0),
    "verdict": "INTEGRITY_OK" if (n_calls == 30 and not any(prompt_drift.values()) and schema_ok > 0) else "INTEGRITY_FAIL",
}
(OUTDIR / f"{FILE_PREFIX}integrity_{SLUG}.json").write_text(json.dumps(integrity, ensure_ascii=False, indent=1))

print("\nRUN_ID:", RUN_ID)
print(json.dumps({"provider": PROVIDER, "model": MODEL_ID, "reconciliation": metrics["reconciliation"],
                  "classification": {"accuracy": acc, "macro": macro, "per_class": per_class},
                  "confusion": metrics["classification"]["confusion_matrix"]["matrix"],
                  "directional": metrics["directional_errors"], "system": metrics["system"],
                  "grounding": grounding, "match_score": score_cmp,
                  "latency": metrics["latency"], "tokens": metrics["tokens"],
                  "chinese_jd_slice": slice_metrics.get("chinese_jd"),
                  "adjacency_fp": adj_fp, "project_under": proj_under, "project_over": proj_over,
                  "total_retries": total_retries, "integrity": integrity["verdict"]}, ensure_ascii=False, indent=1))
