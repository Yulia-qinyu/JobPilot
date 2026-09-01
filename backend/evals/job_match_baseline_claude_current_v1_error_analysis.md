# JobPilot Evaluation — Current Claude Baseline V1 Error Analysis

Fully offline. **0 Anthropic calls · 0 LLM calls · 0 web calls · 0 production-matcher calls.**
No prompt / model / Ground Truth / Dataset / Rubric / production-code change. No fixes implemented.

Inputs: the frozen baseline artifacts (`job_match_baseline_claude_current_v1_*`) + frozen Ground
Truth `job_match_annotation_full_v2_human_verified.json` (`ground-truth-v2`, `rubric annotation-rubric-v2`,
frozen commit `1a31c8d`). Analysis helper: `backend/evals/scripts/analyze_baseline_v1_errors.py`.

---

## 1. Confirmed 100-row accounting

| bucket | count |
|---|---|
| **A. correct + reconciled** | **62** |
| **B. incorrect + reconciled** | **29** |
| **C. unreconciled (system/normalization failure)** | **9** |
| total expected matchable | **100** |

62 + 29 + 9 = 100 (verified against `predictions.json`). The 9 unreconciled are one job
(`tencent:2047239002926510080`) and are **not** classification errors — they are a production
normalization loss (§12).

## 2. Effective Correct Coverage — **0.62**

`ECC = (correct + normalized predictions that match Human GT) / all frozen matchable requirements
= 62 / 100 = 0.62`.

This is a **product/system reliability metric**, not a replacement for Macro F1. Macro F1 (0.692) is
computed on the 91 reconciled rows; ECC is computed on all 100 and therefore also absorbs the 9-row
normalization loss. The gap (0.692 vs 0.62) is exactly the cost of the failed job.

## 3. Directional error matrix (29 reconciled errors)

| transition | count | % of all errors | % of that GT class |
|---|---|---|---|
| **Strong → Partial** | **17** | 58.6% | 32.7% (of 52 GT-Strong) |
| Missing → Partial | 6 | 20.7% | 33.3% (of 18 GT-Missing) |
| Partial → Strong | 4 | 13.8% | 13.3% (of 30 GT-Partial) |
| Partial → Missing | 2 | 6.9% | 6.7% (of 30 GT-Partial) |
| Strong → Missing | 0 | — | — |
| Missing → Strong | 0 | — | — |

**Dominant bias:** the matcher **compresses toward Partial**. It under-credits direct evidence
(Strong→Partial, 17) more than 4× as often as it over-credits (Partial→Strong, 4), and it **never
crosses two steps** (0 Strong↔Missing in either direction). The model is directionally cautious and
"middle-seeking", not erratic.

## 4. Why Partial is the weakest class (F1 0.591)

| | value |
|---|---|
| predicted Partial | 44 |
| genuinely Partial (reconciled) | 27 |
| TP | 21 |
| **FP** | **23** — 17 from GT-Strong (74%), 6 from GT-Missing (26%) |
| FN | 6 |
| Precision | **0.477** · Recall 0.778 · F1 0.591 |

**Only 21 of 44 predicted-Partial rows are actually Partial.** The other 23 are the model using Partial
as a **broad uncertainty bucket**: whenever evidence is "there but not textbook", it lands on Partial
regardless of whether the truth is Strong (17) or Missing (6). Recall is high (0.778) precisely because
Partial is a magnet; precision collapses for the same reason. Fixing Partial precision requires the
model to *commit* — to Strong when a direct project covers the requirement, to Missing when only
adjacent evidence exists.

## 5. Strong → Partial root causes (17)

| group | count | representative cases | likely owner |
|---|---|---|---|
| project / internship evidence underweighted ("经验主要来自实习和个人项目", "作为应届生") | ~9 | `tencent QQ-Agent` "AI Agent/大模型应用/智能助手类经验" (F3 GT-Strong); `tencent 证券` ×3; `tencent 增长` ×3 | **PROMPT_RULE_COMMUNICATION** — frozen rule "a complete direct project can support Strong" is not in `job-fit-v3` |
| completeness / full-flow demanded ("缺少完整…全流程", "从0到1") | subset of above | `tencent AI PM-Agent` "具有完整 AI 产品落地经历" | PROMPT_RULE_COMMUNICATION |
| no explicit metric/outcome → unnecessary downgrade ("缺少可验证成果", "深度案例有限") | ~5 | `tencent 证券` "产品判断力与用户共情"; `tencent 大数据` "数据工作流抽象" | PROMPT_RULE_COMMUNICATION (frozen: "no measurable outcome ≠ automatic downgrade") |
| OR-list: one satisfied alternative not credited | 6 (overlap) | `baidu J98328` "AI领域**或**医疗健康"; `tencent会议评测` "ASR/大模型/智能对话/AI搜索/语音助手" | PROMPT_RULE_COMMUNICATION (frozen `or_alternative_list` rule) |
| specific product/project type not credited ("偏向B端", "C端规模化落地") | ~2 | `tencent 微信输入法` "C端 AI 产品经验" | MODEL_CAPABILITY / PROMPT |

None of the 17 are grounding failures — every one cites valid evidence and then reasons its way to
"…但…" (but…). This is a **calibration / rule-communication** problem, not a retrieval problem, and
not (primarily) raw model capability.

## 6. Missing → Partial root causes (6)

| group | count | example |
|---|---|---|
| **technology adjacency** | 4 | `baidu J84006` general LLM/RAG → "多模态大模型/AIGC/社交娱乐"; `baidu J84492` → "语音交互大模型方向"; `huawei` model-eval → "大模型精度调优/基模/RL训练"; `tencent 微信语音算法` → "流式ASR研发" |
| general model experience credited toward specialised capability | (same rows) | "有模型训练评估经验" offered as partial support for RL/foundation-model training |
| domain adjacency | 1 | `tencent 腾讯云经营` KPay ToB work → "熟悉企业经营管理流程" |
| content-judgement adjacency | 1 | `baidu 大模型策略` product-analysis skill → "内容审美直觉与可拆解方法论" |

**Hypothesis "conceptual/technical adjacency is treated as sufficient for Partial" — CONFIRMED:
5 / 6 (83%)** of GT-Missing→Partial rows cite general or adjacent evidence for a capability the
candidate has no direct evidence for. Owner: **PROMPT_RULE_COMMUNICATION** (no explicit
"adjacent ≠ partial support" guardrail), secondary MODEL_CAPABILITY.

## 7. Partial → Strong root causes (4)

| case | cause |
|---|---|
| `greenhouse` "Tableau/PowerBI/FineBI/SQL" → Strong | **skill-list as deep proficiency** — SQL alone credited as the whole BI toolset ("扎实的数据分析能力") |
| `xsolla` "already uses AI tooling to build/ship faster" → Strong | **project evidence over-generalised** — LLM-integration project read as full AI-assisted-dev proficiency |
| `huawei` "快速掌握新技术的能力" → Strong | project evidence over-generalised (also a borderline matchable/subjective row per GT) |
| `tencent 微信输入法` "系统性思考/问题拆解/从0到1" → Strong | compound: 0→1 ownership claimed from GoFin, but GT holds it Partial (no quantified outcome) |

3 / 4 involve **compound requirements where only one sub-claim is covered** and the model credits the
whole. Owner: **PROMPT_RULE_COMMUNICATION** ("match the narrowest unmet sub-claim"), secondary
MODEL_CAPABILITY.

## 8. Project vs work experience

Frozen adjudication principle: project experience *can* be matchable evidence; when the JD implies a
formal professional role, a project alone normally supports **Partial**; when the JD asks for related
direction / delivery / productization, a complete direct project may support **Strong**.

| bucket | count | examples |
|---|---|---|
| **A. project under-credited** (model went lower than GT while citing the candidate's project/internship as "not formal enough") | **6** | `tencent QQ-Agent`, `tencent AI PM-Agent` "完整落地经历", `tencent 证券` "AI 原生/Agent 完整落地", `tencent 微信输入法` "产品设计与功能策划" |
| **B. project over-credited** (model went higher than GT by over-generalising a project) | **8** | `xsolla` "uses AI to build", `huawei` "快速掌握新技术", `tencent 微信输入法` "系统性思考…0→1", `greenhouse` data-tools (Strong); plus 4 Missing→Partial where a project is cited for a capability it doesn't demonstrate |

Both directions are live. Net: the model does **not** have a single consistent project-vs-work rule —
it under-credits when the requirement wording sounds "senior/formal" and over-credits when the project
is topically close. **Benchmark dimension.**

## 9. OR / alternative-list findings

Strict definition (`source_text` contains 或 / 之一 / 等方向 / 等类产品 — excludes incidental slashes
like 深圳/北京, 训练/推理):

| | value |
|---|---|
| OR-list rows | **18** |
| correct | 8 |
| **incorrect** | **10** |
| unreconciled | 0 |
| **OR-list reconciled accuracy** | **0.44** (vs 0.68 overall) |

**OR-list handling fails in both directions:**
- **Strong → Partial (6):** one listed alternative is clearly satisfied, model downgrades for the
  absent others — `baidu J98328` "熟悉AI领域**或**医疗健康" (AI met); `tencent QQ-Agent` "AI Agent/大模型
  应用/智能助手" (大模型应用 met); `tencent会议评测` "ASR/大模型/智能对话/AI搜索/语音助手" (大模型+智能对话 met);
  `tencent 增长` "用户增长/增长运营/内容平台" (增长运营 met); `tencent AI PM-Agent` "完整落地"; `tencent 证券`
  "AI 原生/Agent/复杂C端".
- **Missing → Partial (4):** an OR-list of capabilities the candidate has *none* of is lifted to
  Partial via adjacency — "多模态/AIGC/社交娱乐"; "语音交互大模型工作或科研"; "企业经营管理流程"; "大模型精度调优/
  基模/RL训练".

OR-list is the **single most concentrated failure slice** (0.44 vs 0.68). Owner: **PROMPT_RULE_COMMUNICATION**
(frozen `or_alternative_list` rule not in the prompt).

## 10. Compound requirement findings

Heuristic compound detector (≥2 markers: joint subclaim / ≥2 `、`-listed items / proficiency-completeness
qualifier / multi-tool list).

| | value |
|---|---|
| compound rows | 13 |
| non-compound rows | 87 |
| compound reconciled error rate | 0.25 |
| non-compound reconciled error rate | 0.33 |
| errors clearly involving incomplete compound coverage | **3** |

Compound rows are **not** measurably worse than non-compound on this small sample — but the 3
identified incomplete-coverage errors are all **Partial→Strong over-credits** (§7). Treat compound
coverage as a benchmark *slice* to watch, not a proven weakness. (Sample too small for a rate claim.)

## 11. Grounding validity vs semantic correctness

| layer | value |
|---|---|
| **A. evidence validity** | **1.000** — every cited id exists in the frozen 30-item catalog (also enforced by `_normalize_matches`, which drops invalid ids). |
| **B. evidence relevance / sufficiency** | **weak** — see below. |
| **C. final label correctness** | **0.681** accuracy. |

**Of the 27 incorrect Strong/Partial predictions, 27 (100%) cite only valid catalog evidence.**
Every wrong match is, by the product's own signal, "evidence-backed". Grounding Rate 1.0 and
Unsupported Match Rate 0.0 say the model **never fabricates or mis-cites evidence** — a real safety
win — but they say **nothing** about whether the cited evidence actually justifies the strength label.

**Product implication:** a match shown to the user as "supported by 3 résumé items" can still be the
wrong strength (usually over-Partial). Grounding is a *safety* metric; it is not a *quality* metric,
and the UI should not present it as one.

## 12. Schema / normalization failure — `tencent:2047239002926510080`

| fact | value |
|---|---|
| matchable requirements submitted | 9 |
| raw rows returned | 10 |
| duplicated `requirement_id` | `reqv2_a6ad3fd74c22598d` (returned twice, identical row) |
| omitted ids | 0 |
| hallucinated ids | 0 |
| all other raw rows valid | yes |
| usable predictions lost | 9 (all of them) |
| job-loss rate | 1 / 30 = **3.3%** |

**Two separate owners, reported separately:**
- **MODEL_CAPABILITY** — the model emitted a duplicate `requirement_id` despite the prompt's explicit
  "no duplicates" instruction. Schema *format* was valid; schema *semantics* (unique id set) were not.
- **PRODUCTION_NORMALIZATION** — `FitAnalysisService._normalize_matches` rejects the **entire job**
  on any id-set violation. 8 otherwise-valid predictions are discarded with **no partial recovery**
  and the job becomes unscorable. This is a deliberate all-or-nothing design choice, not a model
  issue, and it is the reason ECC (0.62) < Macro F1 (0.692).

No fix implemented. If pursued later, a de-dup / repair step before `_normalize_matches` is a
production-code change and must be proposed on its own.

## 13. Full-stack reliability funnel

```
raw schema parse success ........ 30 / 30   (1.000)
        │  loss: 0
job normalization success ....... 29 / 30   (0.967)   ← 1 job lost to duplicate id
        │  loss: 9 requirements
requirement prediction coverage . 91 / 100  (0.910)
        │  loss: 29 wrong labels
effective correct coverage ...... 62 / 100  (0.620)
```

Stage losses: parse 0 · normalize −9 · wrong-label −29 · **usable-correct 62**. The model's *format*
discipline is excellent; the losses are (a) one semantic schema slip amplified by all-or-nothing
normalization, and (b) label calibration.

## 14. GT Match Score vs Baseline Match Score

**GT Match Score** = frozen canonical importance × Human label. **Baseline (production) Match Score**
= model-predicted importance × model label (as production actually computed it). Failed job excluded.

| metric | value |
|---|---|
| jobs comparable | 29 |
| **MAE** (GT vs baseline score) | **13.45 pts** |
| median absolute error | 12 pts |
| max absolute error | **50 pts** (`tencent QQ-Agent`, 1 matchable requirement) |
| jobs with score diff ≥ 20 | **8 / 29** |
| jobs with score diff ≥ 30 | **2 / 29** |
| rank correlation (Spearman, GT vs baseline score) | 0.707 |

Requirement-level label errors propagate into a ~13-point average score error, with tail cases of
25–50 points on small-requirement jobs.

## 15–17. Correlation decomposition — **the key finding**

| pairing (n = 29 comparable jobs) | Spearman | Pearson |
|---|---|---|
| **GT Match Score vs Human Match Fit** | **0.845** | 0.872 |
| **Baseline Match Score vs Human Match Fit** | **0.537** | 0.568 |
| correlation loss attributable to matcher errors | **−0.308** | −0.304 |

**Interpretation (this is the decision-critical result):**

- The **deterministic Match Score construct is sound.** When fed the *human* labels, it ranks jobs
  against holistic Human Match Fit at **Spearman 0.845** — a strong correlation. The matchable-only
  scope, the 5/3/1 weights, and `round_half_up` are not the problem.
- **~0.31 of rank correlation is lost purely to matcher prediction errors** (0.845 → 0.537). The
  Strong→Partial compression and adjacency over-crediting are what drag the *baseline* score away
  from human judgement.
- Therefore: **matcher quality is the dominant lever, not scoring design.** Improving the matcher's
  Strong/Partial calibration should recover most of that 0.31 gap. Redesigning the score would recover
  little (the ceiling with perfect labels is already 0.845, and the residual 0.155 is construct /
  small-N / holistic-perception, per §19).

## 18. Small-N score volatility

| matchable count | jobs | mean HMF | mean GT score | mean baseline abs err | 1-Important-flip score Δ |
|---|---|---|---|---|---|
| 1 | 4 | 4.5 | 100.0 | 12.5 | **≈ 50 pts** |
| 2 | 7 | 3.71 | 76.9 | 14.1 | **≈ 25 pts** |
| 3 | 11 | 3.36 | 67.0 | 12.5 | ≈ 17 pts |
| 4–5 | 4 | 3.5 | 57.2 | 14.8 | ≈ 13 pts |
| 6+ | 4 | 3.5 | 68.0 | 14.7 | ≈ 8 pts |

Mean absolute score error is roughly **constant (~13 pts) across bucket sizes** — the model is not
worse on small jobs. What changes is **step size**: on a 1–2 requirement job, a single label flip
moves the score 25–50 points, so the same error is far more visible.

**Jobs where one label flip moves the score ≥ 25 pts** (all ≤ 2 matchable requirements):
`tencent QQ-Agent` (1 req, GT 100 / baseline 50, Δ50); `tencent AI PM …664448` (2 req, GT 75 /
baseline 38, Δ37); `baidu J84006` (2 req, GT 50 / baseline 75, Δ25); `xsolla` (2 req, GT 75 /
baseline 100, Δ25).

Classification: **DETERMINISTIC_SCORING / UX robustness** — needs a confidence caveat or minimum-
requirement handling; not a matcher-quality issue.

## 19. Human Match Fit outliers (GT labels — NOT model errors)

Jobs where the GT Match Score rank and the Human Match Fit rank diverge by ≥ 8 positions (of 29):

| job | HMF | GT score | matchable count | rank gap |
|---|---|---|---|---|
| 百度 AI产品经理 J84492 | 3 | 80 | 3 | 9.5 |
| 腾讯会议 评测产品经理 | 4 | 70 | 3 | 9.5 |
| 百度 大模型应用平台 J85776 | 4 | 71 | 3 | 8.5 |
| 百度 AI产品经理 J96736 | 4 | 100 | 1 | 8.0 |
| 百度 产品经理实习生 J104146 | 4 | 100 | 1 | 8.0 |
| 腾讯 企业微信基础产品经理 | 4 | 100 | 3 | 8.0 |

All have ≤ 3 matchable requirements. Drivers (validates Match Score semantics, no model involved):

1. **matchable-only construct** — the score ignores eligibility (42 rows) and knowledge (16 rows); a
   job can be capability-covered but eligibility-blocked (or vice versa).
2. **small requirement sets** — 1–3 rows produce coarse ~0/50/100 scores that cannot express a
   nuanced 1–5 fit (J96736 / J104146: 1 requirement each → score pins to 100).
3. **role / domain mismatch** — mismatched-control jobs (Xsolla, 微信语音识别算法) have few matchable
   PM-style rows; the candidate "covers" them while being wrong for the role.
4. **holistic perception** — Human Match Fit integrates seniority realism and role shape that no
   single matchable requirement encodes.

This residual (0.845 not 1.0) is **EVALUATION_DATA_LIMITATION + DETERMINISTIC_SCORING**, not matcher
error.

## 20. Ownership-category summary

| error family | count | primary owner | secondary |
|---|---|---|---|
| Strong → Partial | 17 | **PROMPT_RULE_COMMUNICATION** | MODEL_CAPABILITY |
| Missing → Partial | 6 | **PROMPT_RULE_COMMUNICATION** | MODEL_CAPABILITY |
| Partial → Strong | 4 | **PROMPT_RULE_COMMUNICATION** | MODEL_CAPABILITY |
| Partial → Missing | 2 | **MODEL_CAPABILITY** | — |
| Unreconciled job (9 rows) | 1 job | **PRODUCTION_NORMALIZATION** | MODEL_CAPABILITY |
| Match Score volatility | — | **DETERMINISTIC_SCORING** | — |
| GT-score vs Human-Match-Fit gap | — | **EVALUATION_DATA_LIMITATION** | DETERMINISTIC_SCORING |

Primary-owner tally: PROMPT_RULE_COMMUNICATION ×3 families (27 of 29 label errors),
MODEL_CAPABILITY ×1, PRODUCTION_NORMALIZATION ×1, DETERMINISTIC_SCORING ×1,
EVALUATION_DATA_LIMITATION ×1. **HUMAN_RUBRIC_EDGE_CASE: 0** (Ground Truth is frozen and was not
second-guessed).

**Headline:** ~93% of reconciled label errors trace primarily to the prompt not communicating frozen
rubric rules (OR-list, project-vs-work, adjacency, no-outcome-≠-downgrade, narrowest-unmet-subclaim),
not to raw model capability. This is the most testable and lowest-risk lever.

## 21. Issues suitable for Model Benchmark Round 1

- Strong/Partial calibration (17 Strong→Partial; Strong recall 0.63).
- Technology/domain adjacency reasoning (5/6 Missing→Partial adjacency-driven).
- OR / alternative-list reasoning (OR-list accuracy 0.44).
- Compound-requirement narrowest-unmet-subclaim handling (watch-slice).
- Project-vs-formal-work-experience semantics (6 under, 8 over).
- Proficiency / scope overclaim (4 Partial→Strong).
- Schema adherence — duplicate `requirement_id` emission rate across models / temperatures / repeats.
- Model-tier comparison (is the Strong→Partial compression capacity-bound or prompt-bound?).

## 22. Issues NOT solvable by model selection alone

- **All-or-nothing `_normalize_matches`** — a production-code decision; a better model still loses a
  whole job on one duplicate id. Needs a repair/partial-recovery step (proposed separately).
- **Small-N deterministic Match Score volatility** — 1–2 requirement jobs swing 25–50 pts per flip;
  needs a confidence caveat or minimum-requirement UX rule.
- **Evaluation dataset representativeness** — 27/30 Chinese, 22/30 experienced, 腾讯+百度 = 87%;
  Dataset V2 scope, not a model choice.
- **Match Score construct vs holistic Human Match Fit** — matchable-only by design; the residual gap
  (0.845 → 1.0) is product semantics / documentation, not model quality.

## 23. Ranked Benchmark Round 1 hypotheses

| # | hypothesis | baseline evidence | target metric | failure slice | counts as improvement |
|---|---|---|---|---|---|
| **H1** | **Strong/Partial calibration via rubric-rule communication** (project-can-be-Strong; no-outcome ≠ downgrade) | Strong recall 0.630; 17 Strong→Partial (~9 project-underweight + ~5 no-outcome) | Strong recall, Macro F1 | project_evidence_rows + strong_to_partial | Strong recall ≥ 0.80 **and** Strong precision ≥ 0.80 **and** Missing→Partial errors ≤ 6 (no new adjacency leakage) |
| **H2** | **Technology/domain adjacency guardrail** ("adjacent tech ≠ partial support unless the specific capability is evidenced") | 5/6 Missing→Partial adjacency-driven; Partial precision 0.477 | Missing recall, Partial precision | technology_adjacency_rows | Missing recall ≥ 0.83 **and** no drop in Strong recall |
| **H3** | **OR / alternative-list reasoning** (frozen `or_alternative_list` rule in prompt) | OR-list reconciled accuracy 0.44 (10/18 wrong), both directions | OR-list slice accuracy | or_list_rows | OR-list slice accuracy ≥ 0.85 **and** Macro F1 not lower |
| **H4** | **Narrowest-unmet-subclaim rule for compounds / skill-lists** | 4 Partial→Strong, 3 involve partly-covered compounds; `greenhouse` SQL→full-BI | Partial precision; compound-slice error rate | compound_rows + proficiency_depth_rows | compound-slice error rate ≤ non-compound; Partial precision ≥ 0.60 |
| **H5** | **Schema adherence / duplicate-id robustness across models & temperature** | 1/30 jobs lost to a duplicated `requirement_id` | job normalization success rate; duplicate-id count | all jobs | 30/30 normalization success across 3 repeats; 0 duplicate ids |
| **H6** | **Model-tier comparison at fixed prompt** (capacity vs prompt-bound) | Strong→Partial compression not separable from one run | Macro F1 Δ across Claude tiers, same prompt | full 100 | a larger tier closes ≥ 50% of the Strong recall gap at the **same** prompt ⇒ capacity-bound; else prompt-bound |
| **H7** | **Repeat-run determinism** (deferred from V1) | single run, temp 0, determinism assumed | label agreement across 3 identical runs | full 100 | ≥ 98% label agreement |

Priority order: **H1 ≈ H3 > H2 > H4 > H5 > H6 > H7.** H1+H3 alone address 20+ of the 29 label errors
and, per §17, should recover most of the 0.31 correlation loss. No models selected here; no web
research.

## 24. Proposed benchmark slices (reproducible inclusion rules)

Materialised per-requirement in `job_match_baseline_claude_current_v1_error_slices.csv`
(`is_or_list`, `is_compound`, `transition`, `root_cause_groups`, `importance`,
`matchable_requirement_count` via `score_analysis.csv`).

| slice | inclusion rule |
|---|---|
| `or_list_rows` | `source_text` contains 或 / 之一 / 等方向 / 等类产品 |
| `compound_rows` | `is_compound` = true (≥2 of: joint subclaim, ≥2 `、`-list items, proficiency/completeness qualifier, multi-tool list) |
| `project_based_evidence_rows` | GT or predicted reason references a project/internship (GoFin / KPay / 个人项目 / Product Owner) as the main evidence |
| `formal_work_experience_rows` | `source_text` implies a formal professional role or applies a duration qualifier to a matchable (not eligibility) requirement |
| `technology_adjacency_rows` | GT Missing where the predicted reason credits general/adjacent tech (multimodal / ASR / RL / AIGC / LLM) toward a specialised capability |
| `proficiency_depth_rows` | `source_text` contains 熟练 / 精通 / 深入 / 扎实 / proficient / expert, or a multi-tool list requiring depth |
| `domain_specific_rows` | requirement names a specific industry/domain (证券 / 金融 / 医疗健康 / battery industry / 内容创作) |
| `one_requirement_jobs` | `matchable_requirement_count` == 1 |
| `small_matchable_jobs` | `matchable_requirement_count` ≤ 3 |
| `mismatched_control_jobs` | Dataset V1 `role_category` == mismatched_control (`huawei:28183`, `xsolla:252b30e5`, `tencent:2064981110395420672`) |

## 25. Current baseline decision

| decision | verdict |
|---|---|
| **KEEP_AS_REFERENCE_BASELINE** | **YES.** Honestly measured, fully reproducible, grounding- and schema-format-reliable; it is the fixed anchor for Benchmark Round 1. |
| **KEEP_AS_MODEL_CANDIDATE** | **CONDITIONAL.** Macro F1 0.692, Partial precision 0.477, and 1/30 unscorable jobs are below a comfortable production bar. Retain as a candidate only if Round 1 prompt-rule communication (H1–H4) lifts Macro F1 materially (target ≥ 0.80) and H5 closes the duplicate-id job loss; otherwise compare against a higher Claude tier (H6). |
| **DROP_AS_MODEL_CANDIDATE** | **NO.** No evidence it is worse than untested alternatives. |

Rationale grounded in §17: the scoring construct already reaches Spearman 0.845 with perfect labels,
so the ~0.31 shortfall is recoverable through matcher improvement — and §20 shows ~93% of that
shortfall is prompt-rule communication, the cheapest and lowest-risk fix to test.

## 26. Output files (new; no baseline file overwritten)

- `backend/evals/job_match_baseline_claude_current_v1_error_analysis.json` (structured: summary, classification_errors, directional_errors, partial_analysis, strong_underprediction, missing_to_partial, partial_to_strong, project_vs_work, or_list, compound_requirements, grounding_semantics, schema_failure, system_reliability, score_propagation, correlation_decomposition, small_n_volatility, human_match_fit_construct, ownership, benchmark_relevant_issues, not_solvable_by_model_selection, benchmark_hypotheses, benchmark_slices, baseline_decision)
- `backend/evals/job_match_baseline_claude_current_v1_error_analysis.md` (this file)
- `backend/evals/job_match_baseline_claude_current_v1_error_slices.csv` (100 rows: per-requirement outcome, transition, is_or_list, is_compound, root_cause_groups, grounding flags)
- `backend/evals/job_match_baseline_claude_current_v1_score_analysis.csv` (30 rows: matchable count, HMF, GT Match Score, baseline Match Score (production + frozen-importance variant), abs error)
- `backend/evals/job_match_baseline_claude_current_v1_error_cases_enriched.csv` (38 rows: the incorrect + unreconciled rows enriched)
- `backend/evals/scripts/analyze_baseline_v1_errors.py` (offline analysis helper)

## 27. No API / model / prompt / product / GT change — confirmed

- Anthropic calls: **0** · LLM calls: **0** · web calls: **0** · production-matcher calls: **0** — fully offline (Python analysis over existing artifacts only).
- No prompt / model / temperature / schema / normalization / scoring change.
- `git status --porcelain backend/app backend/alembic frontend` → **empty**.
- `job_match_annotation_full_v2_human_verified.json` read-only (SHA-256 unchanged, `52cda176e166…`, == committed `1a31c8d`).
- Baseline artifacts (`_raw.json`, `_predictions.json`, `_metrics.json`) not modified by this task.
- New code only under `backend/evals/scripts/`.

## 28. git status

```
On branch main — up to date with origin/main
Changes not staged for commit:
        modified:   README.md          ← pre-existing, untouched
Untracked files:
        backend/evals/job_match_baseline_claude_current_v1_*     (12 files: 7 from Baseline V1 + 5 from this analysis)
        backend/evals/scripts/                                   (run_current_claude_baseline_v1.py, analyze_baseline_v1_errors.py)
Last commit: 1a31c8d eval: freeze full 30-job ground truth v2
```
Nothing staged, committed, or pushed.

---

**Baseline Error Analysis V1 completed.**
**Current Claude baseline remains unchanged.**
**Ready for Benchmark Round 1 design.**
