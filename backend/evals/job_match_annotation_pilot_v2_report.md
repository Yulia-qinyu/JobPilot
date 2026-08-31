# JobPilot Ground Truth Annotation Pilot V2 — Generated / Ready for Human Review

## Status

- Taxonomy: **requirement-taxonomy-v2** (eligibility | matchable | knowledge; subjective = non-scoring)
- Milestone commit: `9e09c7b` (feat: separate matchable, eligibility, and knowledge requirements)
- Pilot jobs: **10** (identical to Pilot V1)
- Canonical V2 requirements: **65** (+ **8** subjective expectations)
- AI suggestions only — every `human_*` field blank, every `review_status` = `pending`
- Baseline run: **0** · Model benchmark: **0** · Production Phase 3: **0** · Match Score computed: **0** · App/DB/profile mutations: **0**
- Ground Truth Pilot V2: **not generated** (this file is AI pre-annotation, not human ground truth)

## 1. The 10 Pilot Jobs (same as Pilot V1, resolved to Dataset V1 canonical IDs)

| # | Dataset V1 job_id | Company · Title | City | Role stratum |
|---|---|---|---|---|
| 1 | `baidu:0ad545f8-07df-42f1-9a10-28e79d5dc407` | 百度 · AI 产品经理实习生（J103757） | 北京 | ai_product |
| 2 | `tencent:2088450750270324736` | 腾讯 · AI产品经理-AI平台（Agent）方向 | 深圳 | ai_product |
| 3 | `tencent:2052527703940313088` | 腾讯 · 证券-AI产品经理-金融AI应用体验方向 | 深圳 | ai_product |
| 4 | `veeva:8ae64dee-34a9-4e69-84ef-b91bcde3f35f` | Veeva · Senior Product Manager - AI Agent | 上海 | ai_product (English) |
| 5 | `baidu:105aafd8-a50f-4ef6-aad3-d0a729f5e4a8` | 百度 · 产品经理实习生（J104146） | 北京 | general_product |
| 6 | `tencent:2047239002926510080` | 腾讯 · 金融科技-AI数据产品经理-数据开发方向 | 深圳 | data_product |
| 7 | `tencent:1994013057063473152` | 腾讯 · 企业微信-基础产品经理 | 广州 | general_product |
| 8 | `baidu:f9302c30-aace-449e-8a6d-97c53f4dbf53` | 百度 · 大模型策略产品经理（J97330） | 北京 | strategy_growth_fintech |
| 9 | `tencent:2083093175941115904` | 腾讯 · 腾讯视频-增长产品经理 | 北京 | strategy_growth_fintech |
| 10 | `huawei:28183` | 华为 · AI大模型架构师（训练/推理） | 北京 | mismatched_control |

All 10 IDs resolved cleanly to Dataset V1 canonical job identity; **no sample change**.

## 2. Total V2 Requirements

- **65** canonical scoring-relevant requirements (eligibility + matchable + knowledge)
- **8** subjective expectations (retained as non-scoring context, not canonical rows)
- 73 total annotated items
- Avg canonical per job: **6.5** · min **3** · max **15**

## 3. Taxonomy Counts

| requirement_type | count | share of 65 | in Match Score |
|---|---|---|---|
| eligibility | **14** | 21.5% | no |
| matchable | **45** | 69.2% | **yes** (numerator + denominator) |
| knowledge | **6** | 9.2% | no |
| subjective expectation | **8** | (separate) | no |

Per-job:

| # | Company · Title | elig | match | know | subj | V2 canon | V1 rows |
|---|---|---|---|---|---|---|---|
| 1 | 百度 AI 产品经理实习生 | 1 | 2 | 0 | 1 | 3 | 3 |
| 2 | 腾讯 AI平台（Agent）产品经理 | 2 | 5 | 1 | 1 | 8 | 8 |
| 3 | 腾讯证券 AI 产品经理 | 1 | 6 | 1 | 2 | 8 | 8 |
| 4 | Veeva Senior PM - AI Agent | 1 | 2 | 0 | 0 | 3 | 3 |
| 5 | 百度产品经理实习生 | 2 | 1 | 0 | 1 | 3 | 4 |
| 6 | 腾讯 AI 数据产品经理 | 0 | 9 | 0 | 0 | 9 | 9 |
| 7 | 腾讯企业微信基础产品经理 | 1 | 3 | 0 | 1 | 4 | 4 |
| 8 | 百度大模型策略产品经理 | 1 | 4 | 0 | 1 | 5 | 6 |
| 9 | 腾讯视频增长产品经理 | 2 | 5 | 0 | 0 | 7 | 7 |
| 10 | 华为 AI 大模型架构师 (control) | 3 | 8 | 4 | 1 | 15 | 16 |
| | **Total** | **14** | **45** | **6** | **8** | **65** | **68** |

## 4. Importance Distribution (65 canonical)

| importance | count | notes |
|---|---|---|
| Critical | **14** | all 14 eligibility requirements (V2 forces eligibility → Critical) |
| Important | **39** | 33 matchable + 6 knowledge |
| Preferred | **12** | all matchable (explicit 优先 / 加分 / plus clauses) |

(V1: Critical 14 / Important 40 / Preferred 14 — Critical count coincides but the members differ entirely; V1 Criticals were mostly hard eligibility, now moved out of the scored set.)

## 5. Matchable AI Match-Label Distribution (45 matchable)

| label | count | share |
|---|---|---|
| Strong | **24** | 53% |
| Partial | **13** | 29% |
| Missing | **8** | 18% |

Evidence-grounded matchable rows (Strong or Partial with ≥1 evidence_id): **37** (all Strong/Partial carry evidence; all 8 Missing carry `[]`).

## 6. Eligibility AI Status Distribution (14 eligibility)

| status | count | examples |
|---|---|---|
| Supported | **6** | 已验证学历（Job 1/2/5/8/9/10 degree） |
| PotentialGap | **5** | 明确多年职业年限 vs 2027 应届（Job 3/4/7/9/10 experience_years） |
| Unknown | **3** | Job 2 “一年以上 AI/Agent 产品经验”、Job 5 “可连续实习五个月”（future availability）、Job 10 语言（中文未结构化记录） |

eligibility_category spread: degree 6, experience_years 5, language 1, other 1 (future-availability), graduation_cohort 0, certification 0, work_authorization 0.

## 7. Evidence-Grounded Matchable Rows

**37** of 45 matchable rows are evidence-grounded (Strong/Partial with cited `resume_extracted` / `manual_confirmed` IDs). The 8 Missing rows are concentrated in Job 8 (content-creation domain, 4) and Job 10 (LLM-infra specifics, 3) plus Job 9 R07 (AB testing, 1) — all genuine evidence gaps, not taxonomy artifacts.

## 8. V1 → V2 Differences

### 8.1 Totals

| metric | Pilot V1 | Pilot V2 |
|---|---|---|
| requirement rows | 68 | 65 canonical (+8 subjective) |
| everything got a Strong/Partial/Missing | yes (68/68) | **no** — only 45/65 |
| Match Score denominator (rows that count) | 68 (effective) | **45** (matchable only) |
| V1 label mix | Strong 36 / Partial 22 / Missing 10 | matchable-only: Strong 24 / Partial 13 / Missing 8 |

### 8.2 V1 scored rows now OUTSIDE Match Score — 23 rows

| destination | count | prior V1 labels |
|---|---|---|
| → eligibility | 14 | Strong 7, Partial 6, Missing 1 |
| → knowledge | 6 | Strong 4, Partial 1, Missing 1 |
| → subjective (full row) | 3 | Partial 3 |
| **total removed from Match Score** | **23** | **Strong 11, Partial 10, Missing 2** |

**V1 rows that were previously Strong/Partial/Missing but are now `knowledge`:**

| job | V1 | now |
|---|---|---|
| 腾讯 AI平台（Agent） | R04 Important/Strong「对AI行业趋势和大模型技术有较为深刻的理解和热情」 | knowledge (大模型技术 / AI 行业趋势) |
| 腾讯证券 AI 产品 | R05 Important/Strong「深入了解大模型、Agent、RAG等技术的原理、能力边界与应用场景」 | knowledge (edge case B) |
| 华为架构师 | R09 Important/Strong「具备计算机系统、软件设计、AI模型…专业知识」 | knowledge |
| 华为架构师 | R10 Important/Strong「了解大模型相关的概念和知识」 | knowledge |
| 华为架构师 | R11 Important/Partial「了解大模型训练原理，强化学习原理」 | knowledge |
| 华为架构师 | R13 Important/Missing「了解算子融合、量化、KV压缩、投机推理、PD分离…推理技术」 | knowledge |

**V1 rows that moved to `eligibility`:** every degree / graduation-cohort / minimum-years / language row — Job 1 R01, Job 2 R01+R03, Job 3 R01, Job 4 R01, Job 5 R01+R02, Job 7 R01, Job 8 R01, Job 9 R01+R02, Job 10 R01+R02+R03.

**V1 rows that became purely subjective (removed from score):** Job 5 R03「热爱互联网」(Partial), Job 8 R06「对AI原生应用有极高热情」(Partial), Job 10 R07「对AI Infra领域有强烈兴趣优先」(Partial). Plus 5 attitude fragments newly split out of matchable rows (Job 1 R03, Job 2 R04, Job 3 R04, Job 7 R02, and Job 3's relational素质 sentence).

### 8.3 Compound requirements split differently

- **Job 1**: “本科及以上学历在读…计算机、人工智能等相关专业优先” → eligibility(degree) + matchable-Preferred(major). “对 AI 产品充满热情，有深度使用经验” → subjective + matchable (V1 kept as one matchable).
- **Job 2**: R04 “…有较为深刻的理解和热情” → knowledge(理解) + subjective(热情).
- **Job 3**: R04 “对证券业务有深刻理解或极强的学习意愿” → matchable(理解证券业务) + subjective(学习意愿). R05 kept whole as knowledge.
- **Job 7**: R02 “对产品设计有饱满热情，在功能策划上有…能力” → subjective + matchable.
- **Job 9**: V1's R06/R07 split of “熟练通过数据分析与 AB 实验驱动产品迭代” (数据分析 vs AB 实验) is **preserved** in V2.
- **Job 10**: R06 “能快速接受和掌握新技术，有较强的…学习能力” kept as one matchable/Partial and flagged (matchable vs subjective).

### 8.4 Duplicate / ambiguous requirements removed

- **0** pure duplicates removed (no V1 row was a duplicate).
- V2 explicitly does **not** create a shadow matchable “AI 产品经验” from an `experience_years` eligibility clause — Jobs 2, 3, 4, 7, 9, 10 minimum-years clauses become eligibility only (edge case D).

### 8.5 Requirement IDs that cannot be traced cleanly

- **0** untraceable. All 65 `source_text` values pass an NFKC/casefold substring check against the frozen Dataset V1 fields (`jd_text` / `requirements_text` / `preferred_requirements_text` / `education_requirement` / `experience_requirement`).
- 2 rows are grounded on a **structured eligibility field** rather than free JD prose: Job 7 “三年以上工作经验” and Job 10 “5年以上工作经验” (also echoed in Job 10 `requirements_text`). Documented; both traceable to the frozen dataset.

## 9. How Many Previously Scored Items Left Match Score

- **23** V1 scored rows are removed from the V2 Match Score set (34% of the 68 V1 rows).
- Of those, **12 were V1 Missing or Partial** (10 Partial + 2 Missing) — cases that were dragging scores around for reasons unrelated to evidence-verifiable capability (theoretical understanding, degree/cohort gates, attitude). They are now correctly **outside** evidence-based matching.
- **11 were V1 Strong** — credit the old model was adding to the numerator for things a résumé cannot actually prove (e.g. “理解大模型原理” marked Strong). Removing them makes the score honest.
- Match Score denominator shrinks from an effective **68 → 45** rows.

## 10. Ambiguous Taxonomy Cases

13 flagged (see `job_match_annotation_pilot_v2_need_human_review.csv`):

| # | job | requirement_id | concern |
|---|---|---|---|
| 1 | 百度 AI 实习 | `reqv2_ab313b520bea36f1` | split「充满热情」→subjective vs「深度使用经验」→matchable |
| 2 | 腾讯 Agent | `reqv2_f25785d85ec31cad` | knowledge vs matchable：行业趋势/技术理解部分可由应用经历体现 |
| 3 | 腾讯 Agent | `reqv2_17b2403b35e713d3` | knowledge vs matchable：「与工程师在 Agent 架构层面对焦」 |
| 4 | 腾讯证券 | `reqv2_062e201cf241f5a9` | compound：「理解证券业务」matchable vs「学习意愿」subjective；相邻领域证据 |
| 5 | 百度通用实习 | `reqv2_2343bb0459a84cdc` | eligibility_category=other（未来可用性），Unknown vs PotentialGap |
| 6 | 腾讯 AI 数据 | `reqv2_a6ad3fd74c22598d` | 「了解数仓架构」knowledge vs matchable |
| 7 | 腾讯企业微信 | `reqv2_2c48e151d8271b86` | split「饱满热情」→subjective vs「功能策划能力」→matchable |
| 8 | 百度大模型策略 | `reqv2_8c4d70d605961309` | matchable(专业匹配) vs eligibility(学历相邻) |
| 9 | 百度大模型策略 | `reqv2_6357d38814ca4445` | knowledge(流程理解) vs matchable(创作实操经验) |
| 10 | 华为架构师 | `reqv2_d9c11895b9f4fefd` | language eligibility：中文未结构化记录 → Unknown |
| 11 | 华为架构师 | `reqv2_a7e657643b65384a` | matchable vs subjective：「独立、主动的学习能力」 |
| 12 | 华为架构师 | `reqv2_e0081ebe3ba8d89c` | knowledge vs matchable：「软件设计 / AI 模型」能力可部分由项目证明 |
| 13 | 华为架构师 | `reqv2_1c9199d15075aa37` | matchable Partial vs Missing：一般模型训练 vs 大模型基模 / RL 训练 |

Dominant ambiguity types: **knowledge vs matchable** (5), **compound / subjective split** (4), **eligibility edge** (3), **matchable Partial vs Missing** (1).

## 11. Human-Review Shortlist Size

- **13** of 65 canonical rows (**20%**) flagged for deliberate human inspection.
- The other **52 rows (80%)** are high-confidence and expected to ACCEPT quickly.
- File: `job_match_annotation_pilot_v2_need_human_review.csv`.

## 12. Estimated Human Review Burden — ESTIMATES ONLY, not measured

| review lane | rows | est. rate | est. time |
|---|---|---|---|
| matchable Strong/Partial/Missing review | 45 | ~1.5 min/row | ~68 min |
| eligibility Supported/PotentialGap/Unknown review | 14 | ~1.5 min/row | ~21 min |
| knowledge taxonomy + topic review | 6 | ~1 min/row | ~6 min |
| subjective keep-as-context confirm | 8 | ~0.5 min/row | ~4 min |
| shortlist deep-dive (extra) | 13 | ~3 min/row extra | ~39 min |
| job-level Overall Fit (1–5) | 10 jobs | ~3 min/job | ~30 min |
| **pilot total** | | | **~2.5–3.5 hours** |

- Per job: **~10–20 min** (Jobs 1/4/5 ≈ 6–10 min; Job 10 ≈ 30–40 min).
- Full 30-job annotation projected at similar density: **~7–10 hours** (planning estimate). V2 has fewer canonical rows than V1 (65 vs 68 for these 10) and concentrates deep review on a ~20% shortlist, but adds a taxonomy-decision dimension per row.
- These are planning figures. Record actual time during this pilot before scheduling the remaining 20 jobs.

## 13. File Paths (new files only — Pilot V1 not overwritten)

- `backend/evals/job_match_annotation_pilot_v2.json`
- `backend/evals/job_match_annotation_pilot_v2.csv`
- `backend/evals/job_match_annotation_pilot_v2_guide.md`
- `backend/evals/job_match_annotation_pilot_v2_report.md`
- `backend/evals/job_match_annotation_pilot_v2_need_human_review.csv`

## 14. Dataset V1 — Unchanged

- `job_match_eval_dataset_v1.json` SHA-256 = `3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558` (unchanged)
- `job_match_eval_dataset_v1.csv` SHA-256 = `5d05580595f2f7b92707857a05ac48a93ad32c845bb0b4d4cd06a0734e788d6b` (unchanged)

Dataset V1 was read-only. No byte was modified.

## 15. Ground Truth Pilot V1 — Unchanged

- `job_match_annotation_pilot_v1.json` SHA-256 = `0770bbae8200e7e8cc1a13a6eb6ceed97b1737a0f278017085c472cddd2b58b3` (unchanged)
- `job_match_annotation_pilot_v1.csv` SHA-256 = `bd80b8c6c4287ff88e9b55bd03f15f252391957c3a3012948be88bd82effef2a` (unchanged)

Pilot V1's four files were read-only inputs. Pilot V2 is written to separate `_v2` filenames.

## 16. Candidate Evidence Snapshot — Unchanged

The `candidate_evidence_snapshot` block in Pilot V2 is copied verbatim from Pilot V1:

- `catalog_version` = `candidate-evidence-v2`
- `resume_hash` = `a5c64e177db9454e4562c82bfd3e2dd82aeca613b6b3ba50c5618e66c71e4f4f`
- `experience_bank_hash` = `a96398734f5533bdfa0e35af48a3db35db7b9f7152cf16105abc7b5757affef5`
- allowed: `resume_extracted`, `manual_confirmed`; excluded: `manual_unconfirmed`, `unknown`, `ai_inferred`
- 30-item evidence catalog, identical IDs
- Candidate profile mutations: **0**

Every `ai_evidence_ids` value in Pilot V2 is one of the 30 frozen catalog IDs (validated by the generator).

## 17. No Baseline / Model Benchmark

- Claude baseline runs: **0**
- Model comparison / benchmark: **0**
- Production JD Parser V2 Claude calls: **0** (canonical requirements authored from frozen JD text; only the deterministic `RequirementCatalogBuilder.stable_requirement_id` pure function was used to mint `reqv2_*` IDs — no network, no DB)
- Production Phase 3 / RequirementMatcher runs: **0**
- Match Score computed: **0**
- Accuracy / F1 / precision / recall computed: **0**

## 18. Integrity Checks

| check | result |
|---|---|
| exactly 10 pilot jobs | pass |
| same jobs as Pilot V1 | pass (10/10 resolved to Dataset V1 canonical IDs) |
| Dataset V1 JSON/CSV SHA-256 unchanged | pass |
| Pilot V1 JSON/CSV SHA-256 unchanged | pass |
| every V2 requirement has a canonical `reqv2_*` id | pass (65/65) |
| no duplicate requirement IDs | pass (65 unique) |
| every `source_text` traceable to frozen JD | pass (NFKC/casefold substring) |
| every matchable has `ai_match_label` ∈ {Strong,Partial,Missing} | pass |
| every eligibility has `ai_eligibility_status` ∈ {Supported,PotentialGap,Unknown} | pass |
| knowledge has no Strong/Partial/Missing | pass (`ai_match_label` = N/A) |
| knowledge `ai_evidence_ids` empty | pass |
| `score_included` true only for matchable | pass (45/45) |
| evidence-backed matchable rows cite ≥1 evidence id | pass |
| Missing rows have empty evidence ids | pass |
| all `ai_evidence_ids` in the 30-item frozen catalog | pass |
| `manual_unconfirmed` / inferred evidence used | 0 |
| `human_*` fields populated | 0 |
| all `review_status` = `pending` | pass |
| baseline / model benchmark executed | 0 |
| product / DB / profile state changed | 0 |

## 19. Next Step (Human Only)

Reviewers should ACCEPT / EDIT / REJECT this pilot — starting from the 13-row `need_human_review` shortlist — and fill `human_overall_fit` per job, before any remaining-job annotation, baseline run, model benchmark, prompt change, or final ground-truth creation begins.
