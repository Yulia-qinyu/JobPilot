# Dataset V2 — Balance Report

**Status: NOT_READY.** Accepted corpus = **0 jobs**. Batch 1 produced **10 provisionally
staged jobs** (`dataset_v2_batch1_staging.json`) whose JD text is WebFetch model-rendered
and **not verbatim-verified**, so they are held out of the frozen corpus. All "actual"
figures below are **provisional**, computed on those 10 staged jobs for balance inspection
only. No model was run; no JD text was invented.

## Metadata corrections carried into this report

1. **Dataset V1 requirement baseline** now reads: **158 canonical requirements =
   42 eligibility + 100 matchable + 16 knowledge**. **19 subjective expectations** are
   recorded **separately** (not part of the 158). Source: `human_verified_statistics` in
   `job_match_annotation_full_v2_human_verified.json` (pre-annotation had 17; human review
   added 2). The earlier phrasing "42 + 100 + 16 + 17 subjective across 158" is withdrawn —
   it wrongly folded subjective into the 158 and used the pre-review count.

2. **Career-stage vs employment-type.** Dataset V1 stored a single mixed field
   `{experienced, campus, internship, full-time}`. That is **not** a normalized
   career-stage distribution: `experienced` is a stage; `internship` / `full-time` are
   employment types; `campus` straddles both. **V1 career-stage distribution requires
   normalization before direct comparison** to the V2 frozen enum
   `{campus_new_grad, early_career, experienced, unknown}`. No remapping is invented here;
   the raw V1 field is shown only as raw, flagged.

## Job count

| | target | actual (provisional) |
|---|---|---|
| accepted corpus jobs | 50 min / **60 preferred** / 70 cap | **0** |
| Batch 1 staged (non-verbatim) | — | 10 |
| distinct companies | ≥ 12 / 15–20 preferred | **2** (百度, 京东) — **FAIL (expected)** |

## Company concentration (provisional)

| company | staged | share | vs cap |
|---|---|---|---|
| 百度 | 5 | 50% | over 15% preferred / 20% absolute — **FAIL** |
| 京东 | 5 | 50% | over 15% preferred / 20% absolute — **FAIL** |

Batch 1 was always expected to fail company diversity. **No valid job is deleted to
rebalance** — the fix is more companies in Batch 2.

## City distribution (provisional, primary Mainland city)

| city | staged | note |
|---|---|---|
| 北京市 | 7 | ~70% of staged — too concentrated |
| 深圳市 | 2 | #8/#9 also list 新加坡 (out-of-scope, not counted) |
| 上海市 | 1 | #7 also lists 上海 as a dual city |
| 广州市 | 0 | **gap** |
| 杭州市 | 0 | **gap** |

## Career-stage distribution (provisional, validated against frozen enum)

| stage | staged | target @ 60 |
|---|---|---|
| campus_new_grad | 2 | 12–18 |
| early_career | 0 | 18–24 — **gap** |
| experienced | 6 | 18–27 |
| unknown | 2 | keep small |

One candidate correction: `jd:220156` career_stage **experienced → unknown** (the JD states
no years/seniority; a hard years gate is not inferred). Candidate #6 `employment_type =
internship` is kept as a separate field and was **not** admitted as a career_stage value.

## Role-family distribution (provisional, validated — not blindly from candidate metadata)

| role_family | staged | target @ 60 |
|---|---|---|
| ai_product | 4 | 21–27 |
| platform_enterprise_product | 3 | 6–9 |
| general_product | 2 | 9–12 |
| data_product | 1 | 6–9 |
| strategy_growth_fintech_product | 0 | 6–9 — **gap** |
| mismatched_control | 0 | 3–6 — **gap** |

Validation changes vs candidate metadata: none flipped family, but overlaps were recorded
(#5 general vs growth; #7 platform vs AI-infra; #10 platform vs agent-platform).

## Language distribution (provisional)

| lang | staged | target |
|---|---|---|
| zh | 10 (100%) | ≥ 80% — **PASS** |
| en | 0 | small control subset optional |

## AI-subdomain distribution (provisional tags across 8 AI-relevant staged jobs)

rag_knowledge_systems 2 · ai_platform 2 · agent 2 · speech_asr 2 · ai_consumer_products 2 ·
recommendation_search 2 · enterprise_ai 2 · ai_infrastructure 1 · ai_commercialisation 1 ·
ai_productivity 1 · llm_applications 1 · multimodal 1.
**12 distinct subdomains** — variety target (≥ 8) met on paper, but thin on volume and
missing `ai_tools`.

## Data-quality checks (Batch 1)

| check | result |
|---|---|
| Dataset V1 exact overlap | **3** (candidates #1 #2 #3 = V1 J100665 / J100784 / J100806) → rejected |
| Dataset V1 probable near-duplicate (of the 10 retrieved) | 0 (verbatim re-check pending) |
| within-Batch-1 exact duplicates | 0 |
| within-Batch-1 normalized-title collisions | 1 (`AI产品经理`/京东/北京 → `jd:218961` vs `jd:220156`) — inspected, distinct roles, retained |
| inaccessible / unresolved detail URL | 3 (#6, #15, #16) |
| verbatim JD captured | **0 / 10** — all WebFetch model-rendered |

## Representation check vs V1 — still pending

Company diversity, campus/early-career representation, role-family and AI-subdomain
diversity, and geographic spread cannot be judged against V1 until a verbatim, multi-company
corpus exists. Batch 1 alone reproduces the V1 大厂 concentration (百度/京东 only).

---

## Combined candidate pool after Batch 2 (Batch 1 + Batch 2 = 26 provisional)

See `dataset_v2_batch2_balance_report.{json,md}` for the full A/B/C breakdown. Summary:

| dimension | combined (26) | note |
|---|---|---|
| accepted into corpus | **0** | still 0 |
| source-verified | **0** | Batch 1 WebFetch-rendered; Batch 2 human-pasted, no URLs |
| distinct known companies | **4** (百度 5, 京东 5, 字节跳动 2, 水滴 1) | 13 jobs company=unknown |
| big-tech concentration | 百度+京东 38.5% · +字节 46.2% | at risk vs "avoid Baidu/JD/Tencent" |
| career_stage | campus_new_grad 9 · experienced 7 · unknown 10 · **early_career 0** | early_career is the top gap |
| role_family | ai_product 12 · platform_enterprise 8 · general 3 · data 1 · strategy_growth_fintech 1 · mismatched_control 1 | data/strategy/general/mismatched all thin |
| city | 北京 9 · 深圳 2 · 上海 1 · unknown 14 | 广州/杭州 = 0 |
| language | zh 26 (100%) | PASS |
| distinct AI-subdomains | 13 | broad |
| duplicates | 0 exact / 0 near across pool; 0 vs V1 | Batch 1 had 3 exact V1 dups (already rejected) |

New V2-Real target: **30 preferred / 24 minimum** real Chinese JDs. Raw count (26) meets the
minimum, but 0 are source-verified and the role/stage/company gaps below remain.

---

## Verified-real view (after the revised 3-level provenance policy)

Policy: `dataset_v2_provenance_policy.md`. Provenance is now separated from literal text
fidelity; automated verbatim re-capture is **not** mandatory; the human evaluator is the
provenance authority for manually-copied JDs.

| | count |
|---|---|
| candidate_count (anything staged) | 26 |
| `source_verified` (Level A) | 0 |
| `human_provenance_verified` (Level B — Batch 2, human-confirmed manual copy, `source_url_missing=true`) | 16 |
| `unverified` (Level C — Batch 1, `model_rendered_unverified`) | 10 |
| Dataset V1 duplicates (rejected, not in the pool) | 3 |
| **verified-real ELIGIBLE** (Level A/B, not a V1 dup, enough content, pending final human review) | **16** |
| **verified-real CORPUS** (promoted into `dataset_v2_jobs.json`) | **0** |
| `cleaned_corruption_only` among the eligible 16 | 4 (#1, #4, #6, #14) |

**Quantity language:** the V2-Real minimum (24) is **not** met — `candidate_count = 26` but
`verified_real_eligible = 16` and `verified_real_corpus_count = 0`.

### Gap analysis on the 16 verified-real eligible

| dimension | value |
|---|---|
| career_stage | unknown 8 · campus_new_grad 7 · experienced 1 · **early_career 0** |
| role_family | ai_product 8 · platform_enterprise_product 5 · general_product 1 · mismatched_control 1 · strategy_growth_fintech_product 1 · **data_product 0** |
| known companies | 字节跳动 2 · 水滴 1 → **2 distinct**; unknown 13 |
| city | 北京市 2 · unknown 14 · **广州 / 杭州 / 上海 = 0** |
| AI-subdomain | 10 distinct (llm_applications 9, agent 5, enterprise_ai 4, …) |
| language | zh 16 (100%) |

**Additional verified-real jobs needed: +8 to reach the 24 minimum, +14 to reach the 30
preferred** — chosen to close the cells below, not added blindly.
