# JobPilot Full 30-JD Ground Truth V2 — AI Pre-Annotation Generated / Ready for Human Review

## Status

| field | value |
|---|---|
| artifact type | `ai_pre_annotation` (NOT final human Ground Truth) |
| `status` | `ai_suggestions_pending_human_review` |
| `rubric_id` | `annotation-rubric-v2` (`rubric_freeze_state: frozen`) |
| jobs | **30 / 30** (all of Dataset V1) |
| canonical requirements | **158** (65 pilot verbatim + 93 newly pre-annotated) |
| subjective expectations | **17** (8 pilot + 9 new) |
| milestone commits | product `9e09c7b` · rubric freeze `7f5c77a` |

**Generation:** the 10 frozen Pilot V2 jobs are copied verbatim from the Pilot V2 **pre-annotation** `ai_*` fields (not the human-edited labels); the 20 new jobs were pre-annotated from the frozen Dataset V1 JD text under `annotation-rubric-v2`. Canonical `reqv2_*` IDs come from the production deterministic function `RequirementCatalogBuilder.stable_requirement_id`. **No Claude call, no production semantic matcher, no baseline, no model benchmark, no Match Score, no DB/app mutation.**

## 1. 30 Jobs — exact Dataset V1 IDs, dataset order

Order 1–30 = `[j['job_id'] for j in job_match_eval_dataset_v1.json['jobs']]` (verified identical). The 10 pilot jobs carry `pilot_reference: true` and a **reference-only** `pilot_human_match_fit_reference`; canonical `human_match_fit` is blank on all 30.

Pilot subset (frozen, `pilot_reference: true`): `baidu:0ad545f8…`, `tencent:2088450750270324736`, `tencent:2052527703940313088`, `veeva:8ae64dee…`, `baidu:105aafd8…`, `tencent:2047239002926510080`, `tencent:1994013057063473152`, `baidu:f9302c30…`, `tencent:2083093175941115904`, `huawei:28183`.

New subset (20, `pilot_reference: false`): `baidu:7d5223fc…`, `baidu:6de8b72f…`, `baidu:6182a4d3…`, `baidu:cb813c3a…`, `baidu:423c0fa3…`, `baidu:ff9ed74c…`, `baidu:aa3be39c…`, `tencent:2092538895714664448`, `tencent:2077347119940939776`, `tencent:1978467627152072704`, `tencent:2036621556322562048`, `greenhouse:4186650005`, `tencent:2077246089718837248`, `tencent:2013806539382611968`, `baidu:1270fb70…`, `tencent:2078278970276753408`, `tencent:2041409199149314048`, `xsolla:252b30e5…`, `tencent:2064981110395420672`, `baidu:0f336f8e…`.

## 2. Total Requirements

**158 canonical** requirements + **17 subjective expectations**. avg **5.27** / job, min **3**, max **15** (华为 mismatched control).

## 3. Taxonomy Distribution (158)

| type | ALL 30 | Pilot 10 | New 20 | in Match Score |
|---|---|---|---|---|
| eligibility | **42** (27%) | 14 | 28 | no |
| matchable | **100** (63%) | 45 | 55 | **yes** |
| knowledge | **16** (10%) | 6 | 10 | no |
| subjective (separate) | 17 | 8 | 9 | no |

## 4. Importance Distribution (158)

| importance | ALL 30 | Pilot 10 | New 20 |
|---|---|---|---|
| Critical | **42** | 14 | 28 | (all eligibility) |
| Important | **78** | 39 | 39 |
| Preferred | **38** | 12 | 26 |

## 5. Matchable AI Label Distribution (100 matchable)

| label | ALL 30 | Pilot 10 | New 20 |
|---|---|---|---|
| Strong | **52** (52%) | 24 | 28 |
| Partial | **31** (31%) | 13 | 18 |
| Missing | **17** (17%) | 8 | 9 |

Evidence-grounded matchable rows (Strong/Partial with ≥1 frozen evidence ID): **83** (37 pilot + 46 new).

## 6. Eligibility AI Status Distribution (42 eligibility)

| status | ALL 30 | Pilot 10 | New 20 |
|---|---|---|---|
| Supported | **22** | 6 | 16 |
| PotentialGap | **16** | 5 | 11 |
| Unknown | **4** | 3 | 1 |

New-20 Unknown: only `tencent:1978467627152072704` "一年以上产品工作经验" (borderline 1-year threshold, no confirmed contradiction). Every multi-year (2y/3y/5y) professional gate for the 2027 new-grad candidate → **PotentialGap**; every verified degree gate → **Supported**. Missing evidence was never turned into PotentialGap.

## 7. Subjective Count

**17** subjective expectations (8 pilot + 9 new), all `scored: false`. New examples: “对技术敏感”, “具备快速学习能力”, “积极乐观，抗压性强”, “较强的学习能力和好奇心”, “Genuine passion for building.”

## 8. Pilot 10 vs New 20 — Distribution Comparison

| metric | Pilot 10 | New 20 | note |
|---|---|---|---|
| canonical / job | 6.50 | 4.65 | new JDs are terser (many 2-line Baidu experienced roles) |
| eligibility share | 22% | 30% | new set has more explicit degree + years gates |
| matchable share | 69% | 59% | |
| knowledge share | 9% | 11% | comparable |
| Strong : Partial : Missing | 24:13:8 | 28:18:9 | new set slightly more Partial-heavy |
| eligibility Supported : PotentialGap : Unknown | 6:5:3 | 16:11:1 | new set: more degree-Supported, fewer Unknown |
| evidence-grounded matchable | 37 / 45 (82%) | 46 / 55 (84%) | consistent grounding rate |
| shortlist rate | 20% | 8.6% | new JDs are simpler → less taxonomy ambiguity |

No material drift: taxonomy shares, grounding rate, and label mix are consistent between the human-verified pilot and the new 20. The new set skews toward **eligibility gates + shorter matchable lists** because the non-pilot Dataset V1 jobs are mostly terse experienced-hire postings.

## 9. Human-Review Shortlist

- **21** of 158 rows flagged (**13.3%**) — file `job_match_annotation_full_v2_need_human_review.csv` (13 carried from the frozen pilot + 8 new).
- The other **137 rows (86.7%)** are high-confidence and expected to ACCEPT quickly.

## 10. Top Ambiguity Categories (21 flagged)

| category | count |
|---|---|
| eligibility edge — degree/years "优先" treated as Preferred matchable, or `eligibility_category=other` | 5 |
| knowledge vs matchable — "了解…架构/原理" vs demonstrable practice | 4 |
| compound split — attitude vs capability in one sentence | 3 |
| matchable vs subjective — learning ability / aesthetic sense | 3 |
| requirement duplication — near-synonym knowledge clauses (Baidu 大模型产品经理) | 1 |
| Partial vs Missing — general ML vs foundation-model/RL training adjacency | 1 |
| other (grounding strength, English builder-culture phrasing) | 4 |

## 11. Rubric Edge Cases

**6** documented in `job_match_annotation_full_v2_edge_cases.csv` and the artifact's `rubric_edge_cases`:

1. `baidu:cb813c3a` — "1年及以上产品工作经验优先" → matchable/Preferred (年限措辞 + "优先").
2. `tencent:2064981110395420672` — "硕士及以上学历优先" → matchable/Preferred (degree-level preference, not a gate).
3. `baidu:6de8b72f` — "文字品味 + 洞察 + 规律总结" in one clause → matchable/Partial (aesthetic component near-subjective).
4. `tencent:2013806539382611968` — "熟悉…SQL…等基础概念" → matchable/Partial ("基础概念" phrasing vs verifiable SQL/data practice).
5. `baidu:ff9ed74c` — "对大模型底层技术有一定理解" and "对大模型有基本了解" kept as two knowledge rows (possible duplication; human may merge).
6. `xsolla:252b30e5` — English builder-culture "you build things because you want to… already use AI" → matchable/Partial (attitude + practice blend).

## 12. Possible Rubric Contradictions

**0.** All 6 edge cases are category **(a) ordinary ambiguity** — resolvable within the frozen `annotation-rubric-v2` by the reviewer. None expose a rubric self-contradiction, so **no V2.1 discussion is warranted from this pass**. The rubric was **not** modified.

### Cross-job identical requirement (bookkeeping, not a contradiction)

One new row — `tencent:2013806539382611968` "三年以上工作经验" — has a canonical identity (`source_text`, `normalized_requirement`, `requirement_type`, `source_section`) identical to a frozen pilot row on `tencent:1994013057063473152`. Because `stable_requirement_id` is job-agnostic by design, its natural id collided. The new row was disambiguated with `duplicate_ordinal=1` → `reqv2_1a525cde503f66d0`, keeping all 158 IDs globally unique. Recorded in `cross_job_identical_requirement_disambiguation`. Downstream reconciliation with a fresh production parse of that job should join on `(job_id, normalized_requirement)`.

## 13. Estimated Human Review Burden — ESTIMATES ONLY (not measured)

| lane | rows | est. rate | est. time |
|---|---|---|---|
| matchable Strong/Partial/Missing | 100 | ~1.5 min | ~150 min |
| eligibility Supported/PotentialGap/Unknown | 42 | ~1.5 min | ~63 min |
| knowledge taxonomy + topic only | 16 | ~1 min | ~16 min |
| subjective keep-as-context confirm | 17 | ~0.5 min | ~9 min |
| shortlist deep-dive (extra) | 21 | ~3 min | ~63 min |
| job-level Human Match Fit (1–5) | 30 jobs | ~3 min | ~90 min |
| **full 30-job total** | | | **≈ 6–7 hours** (range 6–10 h) |

If the reviewer accepts the frozen Pilot V2 human-verified Ground Truth for the 10 pilot jobs, the **incremental burden for the new 20** is ≈ 93 rows + 20 Human Match Fit ≈ **4–6 hours**.

## 14. Frozen Candidate Evidence — Confirmed Unchanged

`candidate_evidence_snapshot` is copied byte-identical from the Pilot V2 pre-annotation:

- `catalog_version` = `candidate-evidence-v2`
- `resume_hash` = `a5c64e177db9454e4562c82bfd3e2dd82aeca613b6b3ba50c5618e66c71e4f4f`
- `experience_bank_hash` = `a96398734f5533bdfa0e35af48a3db35db7b9f7152cf16105abc7b5757affef5`
- 30-item catalog; allowed `resume_extracted` / `manual_confirmed` only

Every `ai_evidence_ids` value across all 158 rows is one of the 30 frozen IDs (validated). **No evidence item created.** The Pilot V2 human-only Chinese-native-language adjudication (EDIT C) is **not** in the frozen catalog and was **not** propagated to any of the other jobs — the language row for `huawei:28183` here keeps `ai_eligibility_status = Unknown` (the pre-annotation value).

## 15. Dataset V1 — Unchanged

- `job_match_eval_dataset_v1.json` SHA-256 = `3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558`
- `job_match_eval_dataset_v1.csv` SHA-256 = `5d05580595f2f7b92707857a05ac48a93ad32c845bb0b4d4cd06a0734e788d6b`

Read-only. Dataset composition **not** modified.

## 16. Frozen Pilot Artifacts — Unchanged

| file | SHA-256 |
|---|---|
| `job_match_annotation_pilot_v1.json` | `0770bbae8200e7e8cc1a13a6eb6ceed97b1737a0f278017085c472cddd2b58b3` |
| `job_match_annotation_pilot_v1.csv` | `bd80b8c6c4287ff88e9b55bd03f15f252391957c3a3012948be88bd82effef2a` |
| `job_match_annotation_pilot_v2.json` | `7151e74643929dfba3d86c0f48697836a5216c133f7ad23cb1cbea4ea747924b` |
| `job_match_annotation_pilot_v2.csv` | `0a2bf88a8a29aaec0ff20b30cefe2e737ee937103083ad9ccd9a99d249f592cd` |
| `job_match_annotation_pilot_v2_human_verified.json` | `33481b14226cc29971f0f2c97587e1f3360320e45433155b34bede28a6f4c0ef` |
| `..._human_verified.csv` | `4482ed038093c0d0051b0067923efedcf69e7aa900a1c68a26397bee78097c5b` |
| `..._human_verified_report.md` | `f5c85de46a343ffb954590cb7df38011827a5f5cb888d0bd95e13d3c56199ada` |
| `..._human_verified_changes.csv` | `e2860c1d2a1e45d2d20e5c225085ae9b7e420146566e1fbfc3a1ecd3cb88736e` |

All frozen Pilot V1 / V2 / human-verified / rubric-freeze artifacts are byte-unchanged. The 65 pilot rows carried into this artifact are byte-identical to the frozen Pilot V2 pre-annotation `ai_*` + identity fields (validated: 0 drift).

## 17. Annotation Rubric V2 — Unchanged

`annotation-rubric-v2` (`freeze_state: frozen`) was consumed read-only. No rubric definition, taxonomy, label semantics, Evidence-Verifiability principle, or Human Match Fit definition was modified. Difficult cases were recorded as `rubric_edge_cases`, not rubric changes.

## 18. No Baseline / Model Benchmark

- Claude baseline runs: **0** · production semantic matcher (Phase 3) invocations: **0**
- Model comparison / benchmark: **0** · Match Score computed: **0** · accuracy / F1 / precision / recall: **0**
- The pre-annotation is an annotation-assistance artifact authored from frozen JD text under the frozen rubric; it is **not** a model output and cannot contaminate a future baseline.
- Only deterministic eval helper used: `RequirementCatalogBuilder.stable_requirement_id` (pure hash function, no network, no DB).

## 19. Dataset Representativeness (Dataset V1 — descriptive only, not modified)

| dimension | distribution (30 jobs) |
|---|---|
| recruitment type | experienced **22** · internship **3** · campus **3** · full-time **2** |
| campus / new-grad | **3** (campus) + **3** internship = 6 early-career; **24** experienced/full-time |
| role category | ai_product **15** · general_product **5** · data_product **4** · strategy_growth_fintech **3** · mismatched_control **3** |
| company concentration | 腾讯 **14** · 百度 **12** · Veeva / SES AI / Xsolla / 华为 **1** each |
| language | Chinese **27** · English/other **3** (Veeva, SES AI, Xsolla) |

**Reminder for a future Dataset V2:** prioritise **campus / new-grad full-time** roles (the user's real production distribution), while retaining internship, experienced/full-time, and mismatched-control samples. Company concentration (腾讯 + 百度 = 87%) and Chinese dominance (90%) are existing Dataset V1 limitations carried forward. **Dataset V1 is not modified in this task.**

## 20. Output Files (new — nothing overwritten)

- `backend/evals/job_match_annotation_full_v2_preannotation.json`
- `backend/evals/job_match_annotation_full_v2_preannotation.csv` (158 requirement rows)
- `backend/evals/job_match_annotation_full_v2_preannotation_report.md` (this file)
- `backend/evals/job_match_annotation_full_v2_need_human_review.csv` (21 rows)
- `backend/evals/job_match_annotation_full_v2_edge_cases.csv` (6 rows)

## 21. Next Step (Human Only)

Human reviewers ACCEPT / EDIT / REJECT the 93 new rows (and re-confirm or accept the 65 frozen pilot rows), then assign `human_match_fit` for all 30 jobs, starting from the 21-row shortlist. No baseline run, model benchmark, prompt change, or final Ground Truth creation until Full Human Review is complete.
