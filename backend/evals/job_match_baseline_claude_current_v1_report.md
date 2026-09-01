# JobPilot Evaluation — Current Claude Baseline V1

`run_id: current-claude-baseline-v1-20260901-034331` · single run · temperature 0 · no repeats.

Measures the **current production JobPilot semantic matcher, as-is**, classifying the 100 frozen
matchable requirements from `job-match-ground-truth-v2` against the frozen candidate evidence
snapshot. Ground Truth labels were loaded only after all 30 model calls completed.

**Nothing was optimized, tuned, or changed** — no prompt, model, temperature, schema, system message,
evidence filter, taxonomy, normalization, or Match Score change. The only new code is the eval-only
runner `backend/evals/scripts/run_current_claude_baseline_v1.py` (imports production services, mutates
nothing).

---

## 1. Exact model identifier

| field | value |
|---|---|
| provider | Anthropic |
| model | **`claude-sonnet-4-5-20250929`** (`Settings.claude_model`, from `.env`) |
| structured output | `anthropic` SDK `messages.parse(output_format=FitAnalysisOutput)` (SDK 0.125.0) |

## 2. Production matcher configuration (inspected, unchanged)

| field | value |
|---|---|
| temperature | `0` |
| max_tokens | `4096` |
| matcher prompt version | `job-fit-v3-matchable-only` |
| matcher schema version | `fit-analysis-wire-v2` |
| matcher source SHA-256 | `…` (recorded in `metrics.json.model.matcher_source_sha256`) |
| retry policy | Anthropic SDK default (`max_retries=2`); **no eval-added retries** |
| timeout | Anthropic SDK default |
| prompt/system-message source | `backend/app/services/requirement_matcher.py` (single user message; no system message) |
| response schema | `FitAnalysisOutput{ summary, requirement_matches[], suggested_preparation[] }` |
| normalization | production `FitAnalysisService._normalize_matches` (unchanged) — enforces exact 1:1 requirement-id set, drops evidence ids not in the catalog, downgrades cite-less Strong/Partial to Missing |
| Match Score | production `MatchScoreService` (Critical 5 / Important 3 / Preferred 1 · Strong 1.0 / Partial 0.5 / Missing 0 · `round_half_up`) |

## 3. Number of model calls

**30** — one production Phase-3 semantic call per job (production architecture; every job has ≥1
matchable requirement). No batching change.

## 4. 100 / 100 matchable reconciliation status

**91 / 100 reconciled** by `(job_id, requirement_id)` — exact-key join, no fuzzy/text matching.

The 9 unreconciled requirements are all one job — `tencent:2047239002926510080` (金融科技-AI数据产品经理,
9 matchable requirements). Its raw model output repeated one `requirement_id`
(`reqv2_a6ad3fd74c22598d`, returned twice), so production `_normalize_matches` rejected the **entire
job** ("Claude did not return exactly one match for every requirement"). No id was omitted or
hallucinated — it was a single duplicate row. This is faithful production behavior: any id-set
violation discards the whole job's analysis. Result: those 9 requirements have no prediction and that
job is unscorable.

## 5. Accuracy

**0.681** (62 / 91 reconciled correct).

## 6. Macro Precision — **0.738**
## 7. Macro Recall — **0.692**
## 8. Macro F1 — **0.692**  *(primary model-selection metric)*

## 9–11. Per-class Precision / Recall / F1 (91 reconciled)

| class | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| **Strong** | 0.879 | 0.630 | **0.734** | 29 | 4 | 17 |
| **Partial** | 0.477 | 0.778 | **0.591** | 21 | 23 | 6 |
| **Missing** | 0.857 | 0.667 | **0.750** | 12 | 2 | 6 |

## 12. Confusion matrix (rows = Ground Truth, cols = Prediction)

| GT \ Pred | Strong | Partial | Missing |
|---|---|---|---|
| **Strong** (46) | **29** | 17 | 0 |
| **Partial** (27) | 4 | **21** | 2 |
| **Missing** (18) | 0 | 6 | **12** |

(46 + 27 + 18 = 91 reconciled; GT over the full 100 is 52 / 30 / 18.)

The single dominant error is **GT-Strong → predicted-Partial (17)**. Zero Strong↔Missing confusions
in either direction — the model never wildly over- or under-claims; it compresses toward Partial.

## 13. Grounding Rate — **1.000**

Every predicted Strong/Partial (77 rows) cites ≥1 valid frozen evidence id.

## 14. Unsupported Match Rate — **0.000**

No predicted Strong/Partial cites a non-existent / out-of-catalog evidence id. (Note: `_normalize_matches`
silently drops invalid ids and downgrades cite-less matches, so this is enforced downstream — the raw
model was not audited for pre-normalization invalid ids beyond the id-set check.)

## 15. Evidence ID validity — **1.000**

All 205 predicted evidence ids across reconciled rows exist in the 30-item frozen catalog.
`missing_with_evidence_rate = 0.0`, `matched_with_zero_evidence_rate = 0.0`.

Secondary (human-evidence *set* agreement, not a primary metric): exact-set match 0.19, mean Jaccard
0.42, at-least-one-overlap 0.79. The model picks *valid, relevant* evidence but rarely the exact
human set — expected and acceptable.

## 16. Schema Success Rate — **1.000** parse · **0.967** end-to-end

| metric | value |
|---|---|
| structured-output parse success | 30 / 30 (1.000) |
| normalization success (complete job) | 29 / 30 (0.967) |
| omitted requirements | 9 (all one failed job) |
| duplicate predictions | 1 (the failed job) |
| hallucinated requirement ids | 0 |
| invalid labels | 0 |
| retry count | not exposed by SDK `messages.parse` |

## 17. Latency (30 calls, wall = model since sequential)

| stat | ms |
|---|---|
| total runtime | 632,497 (~10.5 min) |
| mean / call | 21,068 |
| median | 19,858 |
| p90 | 30,584 |
| min / max | 8,681 / 35,983 |

Latency scales with matchable count per job (1-req jobs ~9–11 s; 8–9-req jobs ~30–36 s).

## 18. Token totals

| | tokens |
|---|---|
| input | 127,696 |
| output | 31,365 |
| **total** | **159,061** |
| avg / job | 5,302 |
| avg / requirement | 1,591 |

## 19. Cost

**Unavailable** — no model pricing is present in the repo config, and web pricing lookup was
disallowed for this task. Token usage is reported above; cost can be computed later from an
authoritative rate card.

## 20. 30 job Match Scores (deterministic, model-predicted label × model-predicted importance)

| job | HMF | score | | job | HMF | score |
|---|---|---|---|---|---|---|
| Veeva Sr PM - AI Agent | 3 | 38 | | tencent 光子 AI 数据平台 | 4 | 88 |
| 百度 AI 实习 J103757 | 5 | 100 | | tencent 大数据 PM | 4 | 67 |
| 百度 AI PM J84006 | 3 | 75 | | tencent 金融科技 AI 数据 PM | 4 | **unavailable** |
| 百度 AI PM J84492 | 3 | 90 | | 百度 PM 实习 J104146 | 4 | 100 |
| 百度 AI PM J96736 | 4 | 100 | | 百度 用户 PM J100806 | 5 | 100 |
| 百度 AI PM J98328 | 4 | 80 | | tencent 企业微信基础 PM | 4 | 83 |
| 百度 北京 AI PM J100665 | 5 | 100 | | tencent 腾讯云经营系统 PM | 2 | 64 |
| 百度 大模型 PM J72652 | 4 | 75 | | tencent 会议评测 PM | 4 | 60 |
| 百度 大模型应用平台 PM J85776 | 4 | 71 | | Xsolla AI-First Eng Intern | 3 | 100 |
| tencent AI PM (…664448) | 3 | 38 | | 华为 AI 大模型架构师 | 2 | 58 |
| tencent AI PM-Agent 方向 | 4 | 64 | | tencent 微信语音识别算法 | 2 | 60 |
| tencent QQ-Agent PM | 5 | 50 | | 百度 北京策略 PM J100784 | 5 | 93 |
| tencent 微信输入法 AI PM | 4 | 70 | | 百度 大模型策略 PM J97330 | 2 | 19 |
| tencent 会议 AI PM-ASR | 3 | 33 | | tencent 腾讯视频增长 PM | 4 | 50 |
| tencent 证券 AI PM | 4 | 50 | | SES AI Data Product Manager | 2 | 20 |

Full table with predicted vs GT label breakdown + rank differences in
`job_match_baseline_claude_current_v1_job_scores.csv`.

## 21. Spearman correlation (Match Score vs Human Match Fit) — **0.537**  *(primary)*
## 22. Pearson correlation — **0.568**  *(secondary)*

(29 jobs; the unscorable job excluded.) A **moderate** positive rank correlation. The deterministic
Match Score orders jobs in roughly the same direction as human capability judgement but with
substantial dispersion — driven by (a) small matchable sets (1–3 requirements on many jobs → one label
flips the score 30–50 points), (b) systematic Strong→Partial compression pulling mid-fit scores down,
and (c) a few sharp divergences (`xsolla` HMF 3 / score 100; `tencent QQ-Agent` HMF 5 / score 50;
`tencent 腾讯云经营` HMF 2 / score 64).

**Interpretation caveat (§18 of the task):** the Match Score is **not** overall applicant suitability.
It measures *verified career-evidence coverage of matchable requirements only*. Eligibility (42 rows,
deterministic, separately adjudicated) and knowledge (16 rows, non-scoring) are excluded by design.

## 23. Top error categories (38 wrong of 100; `…_errors.csv` has the bucket per row)

| # | bucket | count |
|---|---|---|
| L | **schema / normalization failure** — one job's raw output repeated a `requirement_id`; production discards the whole job | **9** |
| B | **Partial overprediction** (GT Strong → Partial, generic conservatism / "缺少完整案例", "深度案例有限") | 8 |
| E | **technology / domain adjacency over-credited** (GT Missing → Partial: general AI/LLM experience credited toward multimodal / ASR / RL-training / AIGC) | 6 |
| D | **project experience under-credited** vs the GT rule that a complete, direct project can support Strong (model: "经验主要来自实习和个人项目", "作为应届生") | 6 |
| J | **proficiency / depth / scope overclaim** (GT Partial → Strong: SQL credited as full BI toolset; "uses AI to build" → Strong) | 4 |
| G | **OR-list mishandling** (GT Strong → Partial: one satisfied listed alternative not credited because others are absent) | 3 |
| I | **available adjacent evidence missed** (GT Partial → Missing: Veeva "企业 SaaS/可配置平台"; 华为 "算法工作经验") | 2 |

**Headline:** 23 of 44 predicted-Partial rows are false positives. The matcher is systematically
**more conservative than the human rubric on Strong** (17 GT-Strong compressed to Partial) and
**too generous on Missing** (6 GT-Missing lifted to Partial via technology adjacency). Precision on
Partial is only 0.48.

## 24. Most informative failure cases

1. **`tencent:2047239002926510080` — job-level schema failure.** Raw output listed
   `reqv2_a6ad3fd74c22598d` twice (identical). `_normalize_matches` rejected all 9 matches. One
   duplicated row cost an entire job. *Highest-leverage fix target — deterministic, not a judgement
   problem.*
2. **`baidu:cb813c3a` "熟悉 AI 领域或医疗健康行业" — GT Strong → Partial (bucket G).** JD is an
   explicit OR; candidate clearly meets "AI 领域". Model: "在医疗健康行业方面没有直接经验" → downgraded.
   The frozen rubric's OR-list rule (meeting one alternative is not downgraded for missing others) is
   not reflected in the production prompt.
3. **`tencent:2077347119940939776` (QQ-Agent) "AI Agent / 大模型应用 / 智能助手类产品经验" — GT Strong (edit
   F3) → Partial (bucket D+G).** Model: "经验主要来自实习和个人项目, 缺少完整的…从 0 到 1 的产品经理经验".
   Human GT credits GoFin's LLM/Agent productization as meeting one permitted direction. This job has
   only 1 matchable requirement, so the miss moves its score 100 → 50 (HMF 5).
4. **`baidu:7d5223fc` "多模态大模型应用 / AIGC / 社交娱乐类产品经验" — GT Missing → Partial (bucket E).** Model
   cited general LLM/RAG evidence (`resume_extracted:21/28/ai_experience:0/4`) as partial support for
   a *multimodal / AIGC / entertainment* requirement the candidate has no evidence for.
5. **`huawei:28183` "大模型精度调优 / 基模 / RL 训练经验" — GT Missing (edit B) → Partial (bucket E).** Model:
   "有模型训练评估和性能评估经验" → Partial. Human GT: general ML training ≠ foundation-model / RL
   training; adjacency insufficient.
6. **`greenhouse:4186650005` "data analysis tools (Tableau / PowerBI / FineBI / SQL)" — GT Partial →
   Strong (bucket J).** Candidate has SQL only; model credited the whole BI-tool list as Strong on
   SQL + "扎实的数据分析能力".
7. **`xsolla:252b30e5` "already uses AI tooling to build/ship faster" — GT Partial → Strong (bucket
   J).** Model over-read LLM-integration project work as full "AI-assisted development" proficiency.
   2-requirement job → score 100 vs HMF 3.
8. **`veeva:8ae64dee` "企业 SaaS / 可配置平台 / 多租户产品经验" — GT Partial → Missing (bucket I).** GT cites
   `resume_extracted:28` (GoFin configurable platform) as adjacent partial support; model found
   "暂未找到支持该要求的证据".
9. **`tencent:2083093175941115904` (增长 PM) — 3 of 5 matchable rows GT Strong → Partial (bucket B/D).**
   增长运营 / 增长方法论 / 数据驱动迭代 all downgraded citing "缺乏明确的…直接证据" / "未体现完整体系".
   Consistent conservatism concentrated in one job → score 50 vs HMF 4.
10. **`tencent:2052527703940313088` (证券 AI PM) — 3 of 6 rows GT Strong → Partial (bucket B).** Same
    pattern: "缺少具体案例" / "深度案例不足" on capabilities the human GT accepts as Strong from GoFin.

## 25. Is the current baseline good enough to keep as a candidate?

**Marginal — keep as the reference baseline, but it is below a comfortable production bar.**

- **Grounding and schema-format reliability are strong** (grounding 1.0, parse 1.0, no hallucinated
  ids/evidence, no invalid labels). The evidence discipline is not the problem.
- **Macro F1 0.69 is mediocre for a 3-class task** and is dragged down almost entirely by
  **Partial precision 0.48**. The model does not distinguish "solid direct evidence" (Strong) from
  "adjacent / partial" (Partial) the way the frozen rubric does.
- **The all-or-nothing job failure on a single duplicated id is a real availability risk** — 1 in 30
  jobs here produced zero usable output and an unscorable job, with no partial recovery.
- **Match-Score↔Human-Match-Fit Spearman 0.537** is only moderate; small matchable sets make the
  deterministic score jumpy.

It is a legitimate, honestly-measured baseline to improve against. It is not yet a "ship it" result.

## 26. Hypotheses to test in Model Benchmark Round 1

Diagnosis only — **no prompt/model change is proposed or made here.**

1. **Strong/Partial threshold calibration.** The prompt's Strong criterion ("direct, convincing
   evidence") is being read more strictly than the human rubric. Test whether wording that credits a
   *complete, directly relevant project* as Strong (per the frozen `project_vs_work_experience` rule)
   raises Strong recall (0.63) without cratering Partial recall.
2. **OR / alternative-list handling.** 3 GT-Strong misses are explicit OR clauses where one
   alternative is met. Test adding the frozen `or_alternative_list` rule to the prompt.
3. **Technology-adjacency guardrail.** 6 GT-Missing→Partial errors are general-AI experience credited
   toward multimodal / ASR / RL / AIGC. Test an explicit "adjacent technology is not partial support
   unless the specific capability is evidenced" instruction.
4. **Duplicate-id robustness.** Either (a) a benchmark variant that de-dups/repairs the raw id set
   before `_normalize_matches`, or (b) measure how often other models/temperatures emit duplicates.
   Currently 1/30 → ~3% job-loss rate. (Product-code change, if pursued, is out of scope for
   benchmarking and must be proposed separately.)
5. **Proficiency-scope overclaim.** 4 GT-Partial→Strong on "list of tools / broad capability, only
   part evidenced". Test a "match the *narrowest* unmet sub-claim" instruction.
6. **Small-N score volatility.** Not a model issue — flag for the scoring/UX discussion whether jobs
   with ≤2 matchable requirements should surface a confidence caveat.
7. **Model comparison.** Run the same 30-call protocol on at least one alternative Claude tier to see
   whether the Strong→Partial compression is model-capacity-bound or prompt-bound.
8. **Repeat-run variance** (deferred from V1): 3× at temperature 0 to confirm determinism and quantify
   any residual nondeterminism before drawing benchmark conclusions.

## 27. Ground Truth unchanged — confirmed

`job_match_annotation_full_v2_human_verified.json` SHA-256 `52cda176e166146ffc24a85067f13618c5f717cedab506f0ba17fe5e701ba050`
— identical to the committed frozen artifact (`git show 1a31c8d:…`). No human label, eligibility
status, evidence id, Human Match Fit, taxonomy, or requirement identity read into the model input;
loaded only for post-hoc scoring.

## 28. Dataset V1 unchanged — confirmed

`job_match_eval_dataset_v1.json` `3654d64c…b2b558` · `.csv` `5d055805…88d6b`. Read-only (JD text only,
for source-context display in `errors.csv`).

## 29. Candidate evidence unchanged — confirmed

Built the production `EvidenceCatalog` directly from the frozen `candidate_evidence_snapshot`
(`resume_hash a5c64e17…e4f4f`, `experience_bank_hash a9639873…affef5`, 30 items, `resume_extracted`
/ `manual_confirmed` only). No live DB query, no resume re-parse, no Experience Bank load. The
human-only GoFin C-end / AI-platform / Chinese-native adjudication facts were **not** in the catalog
and did not reach the model.

## 30. No prompt / model / product change — confirmed

No file under `backend/app/`, `backend/alembic/`, `frontend/` was modified
(`git status --porcelain backend/app backend/alembic frontend` → empty). `requirement_matcher.py`,
`claude_client.py`, `match_score.py`, `fit_analysis_service.py` unchanged. No DB mutation, no
Candidate Profile mutation, no Rubric change. Only new file: the eval-only runner under
`backend/evals/scripts/`.

## 31. Output file paths

- `backend/evals/job_match_baseline_claude_current_v1_raw.json` (30 calls: submitted requirements, evidence catalog, parsed model output, normalized output, latency, tokens, schema/normalization status)
- `backend/evals/job_match_baseline_claude_current_v1_predictions.json`
- `backend/evals/job_match_baseline_claude_current_v1_predictions.csv` (100 rows)
- `backend/evals/job_match_baseline_claude_current_v1_job_scores.csv` (30 rows)
- `backend/evals/job_match_baseline_claude_current_v1_metrics.json`
- `backend/evals/job_match_baseline_claude_current_v1_errors.csv` (38 rows, `error_bucket` per row)
- `backend/evals/job_match_baseline_claude_current_v1_report.md` (this file)
- `backend/evals/scripts/run_current_claude_baseline_v1.py` (reproducible runner)

## 32. git status

```
On branch main — up to date with origin/main
Changes not staged for commit:
        modified:   README.md          ← pre-existing, untouched
Untracked files:
        backend/evals/job_match_baseline_claude_current_v1_*   (7 files)
        backend/evals/scripts/run_current_claude_baseline_v1.py
Last commit: 1a31c8d eval: freeze full 30-job ground truth v2
```
Nothing staged, committed, or pushed. `git status --porcelain backend/app backend/alembic frontend` → empty.

---

**Current Claude Baseline V1 completed.**
**Ground Truth remained frozen.**
**Ready for baseline error analysis / model benchmark planning.**
