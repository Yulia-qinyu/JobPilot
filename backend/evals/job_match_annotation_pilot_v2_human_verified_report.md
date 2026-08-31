# JobPilot Ground Truth Annotation Pilot V2 — Human Verified / Rubric V2 Frozen

## Status

| field | value |
|---|---|
| `status` | `human_verified_pilot_v2` |
| `review_complete` | `true` |
| `reviewed_requirements` | **65 / 65** |
| `human_match_fit_jobs` | **10 / 10** |
| `freeze_state` | `frozen` (consistency pass passed 2026-09-01) |
| `frozen_rubric_id` | `annotation-rubric-v2` |
| `rubric_version` | `requirement-taxonomy-v2 / annotation-rubric-v2` |
| milestone commit | `9e09c7b` |

**Annotation Rubric V2 is FROZEN** (`annotation-rubric-v2`, frozen 2026-09-01). This was a metadata-only freeze: no human label, requirement, evidence, taxonomy, canonical `reqv2_*` id, Human Match Fit value, or source content was changed.

Human adjudication applied to the AI pre-annotation (`job_match_annotation_pilot_v2.json`). All `ai_*` fields preserved verbatim; only `human_*`, `review_status`, job-level `human_match_fit` / `human_overall_fit` populated, plus one subjective expectation added per EDIT A. No Claude call, no model benchmark, no product/DB/profile mutation.

## 1. The 10 Jobs (unchanged from pre-annotation / Pilot V1)

| # | job_id | Company · Title | Human Match Fit |
|---|---|---|---|
| 1 | `baidu:0ad545f8-07df-42f1-9a10-28e79d5dc407` | 百度 · AI 产品经理实习生（J103757） | **5** |
| 2 | `tencent:2088450750270324736` | 腾讯 · AI产品经理-AI平台（Agent）方向 | **4** |
| 3 | `tencent:2052527703940313088` | 腾讯 · 证券-AI产品经理-金融AI应用体验方向 | **4** |
| 4 | `veeva:8ae64dee-34a9-4e69-84ef-b91bcde3f35f` | Veeva · Senior Product Manager - AI Agent | **3** |
| 5 | `baidu:105aafd8-a50f-4ef6-aad3-d0a729f5e4a8` | 百度 · 产品经理实习生（J104146） | **4** |
| 6 | `tencent:2047239002926510080` | 腾讯 · 金融科技-AI数据产品经理-数据开发方向 | **4** |
| 7 | `tencent:1994013057063473152` | 腾讯 · 企业微信-基础产品经理 | **4** |
| 8 | `baidu:f9302c30-aace-449e-8a6d-97c53f4dbf53` | 百度 · 大模型策略产品经理（J97330） | **2** |
| 9 | `tencent:2083093175941115904` | 腾讯 · 腾讯视频-增长产品经理 | **4** |
| 10 | `huawei:28183` | 华为 · AI大模型架构师（训练/推理） | **2** |

## 2. Requirements

**65** canonical requirements reviewed (65 / 65). Canonical `reqv2_*` IDs unchanged — no requirement identity (`source_text` / `normalized_requirement` / `requirement_type` / `source_section`) was altered, so every ID is preserved. 0 duplicates.

## 3. Accepted count

**60** requirements accepted as pre-annotated (`review_status = accepted`, `human_accept_reject = accept`, `human_taxonomy_decision = "accepted AI taxonomy"`). This includes the 10 explicitly-listed previously-flagged disputed items (§6 of the adjudication).

## 4. Edited count

**5** requirements edited (`review_status = edited`, `human_accept_reject = accept`) — edits A–E below. No taxonomy type changed; edits only adjust the human match/eligibility label (and, for EDIT A, split a subjective phrase out of scoring).

## 5. Rejected count

**0**. No scoring requirement was rejected.

## 6. Final Taxonomy Distribution

| type | count | in Match Score |
|---|---|---|
| eligibility | **14** | no |
| matchable | **45** | yes |
| knowledge | **6** | no |
| subjective expectation | **9** | no (8 from pre-annotation + 1 added by EDIT A) |

Unchanged from pre-annotation except the +1 subjective expectation.

## 7. Final Matchable Label Distribution (45 matchable, human)

| label | pre-annotation (AI) | human verified | delta |
|---|---|---|---|
| Strong | 24 | **22** | −2 (EDIT D, EDIT E) |
| Partial | 13 | **14** | +2 −1 (EDIT D, E in; EDIT B out) → net +1 |
| Missing | 8 | **9** | +1 (EDIT B) |

## 8. Final Eligibility Status Distribution (14 eligibility, human)

| status | pre-annotation (AI) | human verified | delta |
|---|---|---|---|
| Supported | 6 | **7** | +1 (EDIT C) |
| PotentialGap | 5 | **5** | — |
| Unknown | 3 | **2** | −1 (EDIT C) |

## 9. Final Human Match Fit — values + distribution

| # | Job | Human Match Fit |
|---|---|---|
| 1 | 百度 AI 产品经理实习生 | 5 |
| 2 | 腾讯 AI平台（Agent）产品经理 | 4 |
| 3 | 腾讯证券 AI 产品经理 | 4 |
| 4 | Veeva Senior PM - AI Agent | 3 |
| 5 | 百度产品经理实习生 | 4 |
| 6 | 腾讯 AI 数据产品经理 | 4 |
| 7 | 腾讯企业微信基础产品经理 | 4 |
| 8 | 百度大模型策略产品经理 | 2 |
| 9 | 腾讯视频增长产品经理 | 4 |
| 10 | 华为 AI 大模型架构师 (control) | 2 |

Distribution: **5 → 1 job · 4 → 6 jobs · 3 → 1 job · 2 → 2 jobs · 1 → 0 jobs.**

**Human Match Fit definition:** 忽略招聘资格门槛、招聘类型和个人投递意愿，只看候选人当前已验证的经历、技能和岗位的 matchable requirements，这个岗位与候选人的能力匹配程度如何？ (5 = Very Strong … 1 = Clearly Unsuitable). It excludes recruitment type, internship-vs-campus preference, willingness to apply, city, company, compensation, and eligibility blockers — it exists only to validate matchable-requirement alignment / Match Score quality.

`human_match_fit` is the canonical evaluation field. `human_overall_fit` is retained as a backward-compatible alias with the identical value.

## 10. The Exact 5 Human Edits

| edit | requirement_id | job | type | AI → Human | rationale (human_grounding_reason) | review_status |
|---|---|---|---|---|---|---|
| **A** | `reqv2_a7e657643b65384a` | 华为 AI大模型架构师 | matchable | Partial → **Partial** (label unchanged) | 保留“快速掌握新技术的能力”为 matchable/Partial；同句“独立、主动的学习能力”移出评分，作为 subjective expectation（见 §11）。 | edited |
| **B** | `reqv2_1c9199d15075aa37` | 华为 AI大模型架构师 | matchable | Partial → **Missing** | 冻结证据仅支持一般模型训练辅助与模型性能评估，不能直接证明大模型精度调优、基模训练或强化学习训练经验；技术相邻不足以判为 Partial。`human_evidence_ids = []`。 | edited |
| **C** | `reqv2_d9c11895b9f4fefd` | 华为 AI大模型架构师 | eligibility | Unknown → **Supported** | 英语工作能力由已验证简历语言事实（`resume_extracted:resume:1:skills:16`）支持；中文为候选人人工确认的母语，因此该语言门槛整体判为 Supported。 | edited |
| **D** | `reqv2_7d915e68d837899a` | Veeva Senior PM - AI Agent | matchable | Strong → **Partial** | 已有 AI/LLM 产品交付、RAG 与模型评估实践，但冻结证据不足以直接证明 prompt/context engineering 与 human-in-the-loop workflow 的完整实践覆盖。保留原有有效证据 IDs。 | edited |
| **E** | `reqv2_c2f1c7d80e0cbd8a` | 华为 AI大模型架构师 | matchable | Strong → **Partial** | Python 有明确项目实践；C/C++ 目前仅有技能声明，没有直接项目/开发证据，两类语言未都达到“熟练掌握”。保留 Python 与 C/C++ 证据 IDs。 | edited |

**EDIT C note (Ground-Truth-only):** 中文母语属于本次人工 Ground Truth 确认事实；不因此新增 JobPilot 产品字段，也不修改 Candidate Profile；该 edge case 不升级为产品需求。The frozen candidate evidence snapshot was **not** mutated and **no** new evidence item was added — `human_evidence_ids` for EDIT C remains `["resume_extracted:resume:1:skills:16"]` (the English fact); the Chinese-native fact lives only in `human_grounding_reason` / `human_notes` as an adjudication note.

## 11. Subjective Change from EDIT A

One subjective expectation was **added** to job `huawei:28183`:

- `text`: **“独立、主动的学习能力”**
- `source_text`: “4. 能快速接受和掌握新技术，有较强的独立、主动的学习能力。”
- `scored`: `false` · `requirement_type`: `subjective` · `human_keep_as_context`: `keep`
- `parent_requirement_id`: `reqv2_a7e657643b65384a`
- `added_by`: `EDIT A`

Huawei job subjective expectations after the edit: `["对 AI Infra 领域有强烈兴趣", "独立、主动的学习能力"]`. Total subjective expectations across the pilot: 8 → **9**. **No new scoring requirement** was created for the phrase.

## 12. Canonical IDs Preserved

All **65** `reqv2_*` requirement IDs are byte-identical to the pre-annotation artifact. No `source_text`, `normalized_requirement`, `requirement_type`, `source_section`, `importance`, `knowledge_topics`, `ai_evidence_ids`, or `score_included` value was changed. 65 unique IDs, 0 duplicates. Ground Truth V2 remains directly joinable to production `structured_jd.requirements[].requirement_id` / `requirement_matches[].requirement_id` / `score_basis.included_requirement_ids`.

## 13. Candidate Evidence Snapshot — Unchanged

`candidate_evidence_snapshot` is copied verbatim from the pre-annotation (which itself copied Pilot V1):

- `catalog_version` = `candidate-evidence-v2`
- `resume_hash` = `a5c64e177db9454e4562c82bfd3e2dd82aeca613b6b3ba50c5618e66c71e4f4f`
- `experience_bank_hash` = `a96398734f5533bdfa0e35af48a3db35db7b9f7152cf16105abc7b5757affef5`
- 30-item catalog, identical IDs; allowed `resume_extracted` / `manual_confirmed` only

Every `human_evidence_ids` value is one of the 30 frozen catalog IDs (validated). No evidence item added; candidate profile mutations: 0.

## 14. Dataset V1 — Unchanged

- `job_match_eval_dataset_v1.json` SHA-256 = `3654d64c0f94e507e91343706bd79ca6b20f8081ee22880bf537744d88b2b558`
- `job_match_eval_dataset_v1.csv` SHA-256 = `5d05580595f2f7b92707857a05ac48a93ad32c845bb0b4d4cd06a0734e788d6b`

Read-only throughout. **Dataset V1 remains frozen.**

## 15. Pilot V1 — Unchanged

- `job_match_annotation_pilot_v1.json` SHA-256 = `0770bbae8200e7e8cc1a13a6eb6ceed97b1737a0f278017085c472cddd2b58b3`
- `job_match_annotation_pilot_v1.csv` SHA-256 = `bd80b8c6c4287ff88e9b55bd03f15f252391957c3a3012948be88bd82effef2a`

## 16. Pilot V2 Pre-Annotation — Unchanged

- `job_match_annotation_pilot_v2.json` SHA-256 = `7151e74643929dfba3d86c0f48697836a5216c133f7ad23cb1cbea4ea747924b`
- `job_match_annotation_pilot_v2.csv` SHA-256 = `0a2bf88a8a29aaec0ff20b30cefe2e737ee937103083ad9ccd9a99d249f592cd`
- `job_match_annotation_pilot_v2_guide.md` SHA-256 = `2bad60bb5887689e22a4fd11d6e8dd1d60c21dd1a76cf8982d52ccebefabc8b9`
- `job_match_annotation_pilot_v2_report.md` SHA-256 = `8a9acc8704aecc896e996fb5255bb71965d6f6e671139e10cbeb96b33e0837fe`
- `job_match_annotation_pilot_v2_need_human_review.csv` SHA-256 = `c95d635c79aaf8e07d1be5259fbaaf266c095303eb04086377c9260d9bdead8a`

All five pre-annotation files were read-only inputs.

## 17. No Product Code Modified

No file under `backend/app/`, `backend/alembic/`, `frontend/`, or any production schema/service was touched. This task added only new `backend/evals/*_human_verified*` files. No DB state, no application state, no `CandidateProfile` change.

## 18. No Baseline / Model Benchmark

Claude baseline: **0** · model comparison / benchmark: **0** · production Phase 3 / matcher: **0** · Match Score computed: **0** · accuracy / F1: **0**. The adjudication was applied mechanically from the explicit decisions; nothing was recomputed or reinterpreted.

## 19. Consistency Validation (all pass)

| check | result |
|---|---|
| exactly 10 jobs | pass |
| exactly 65 canonical requirements | pass |
| every requirement reviewed | pass |
| no `pending` review_status remains | pass |
| 60 accepted + 5 edited | pass |
| 0 rejected scoring requirements | pass |
| every matchable has human_match_label ∈ {Strong,Partial,Missing} | pass |
| every eligibility has human_eligibility_status ∈ {Supported,PotentialGap,Unknown} | pass |
| every knowledge has human_match_label = N/A | pass |
| every knowledge human_evidence_ids empty | pass |
| score_included true only for matchable (45/45) | pass |
| canonical `reqv2_*` IDs unchanged (65/65) | pass |
| no duplicate requirement IDs | pass |
| no unsupported evidence IDs introduced | pass |
| Missing rows have empty human_evidence_ids | pass |
| candidate evidence snapshot hashes unchanged | pass |
| Dataset V1 hashes unchanged | pass |
| Pilot V1 hashes unchanged | pass |
| Pilot V2 pre-annotation hashes unchanged | pass |
| Human Match Fit distribution = {5:1, 4:6, 3:1, 2:2} | pass |
| no product code changed / no DB state changed | pass |
| no baseline / model benchmark executed | pass |

## 20. Dataset V2 Note (planning only — Dataset V1 stays frozen)

For a future **Dataset V2**, the evaluation dataset should better reflect the user's real production distribution:

- **prioritize campus / new-grad full-time roles** (校招 / 应届全职) as the primary stratum;
- retain some **internship** and **experienced (社招)** roles as controls;
- retain **mismatched** roles as controls (e.g. the current 华为 AI 大模型架构师).

Do **not** modify Dataset V1 — it remains frozen. This note is guidance for later dataset construction only.

## 21. Output Files (new — pre-annotation preserved)

- `backend/evals/job_match_annotation_pilot_v2_human_verified.json`
- `backend/evals/job_match_annotation_pilot_v2_human_verified.csv`
- `backend/evals/job_match_annotation_pilot_v2_human_verified_report.md` (this file)
- `backend/evals/job_match_annotation_pilot_v2_human_verified_changes.csv` (5 requirement edits + 10 Human Match Fit values + 1 EDIT-A subjective addition = 16 rows)

## 22. Next Step

The final consistency pass passed on 2026-09-01 and **Annotation Rubric V2 (`annotation-rubric-v2`) is now frozen**. Subsequent annotation of the remaining Dataset V1 jobs, baseline runs, model benchmarks, and prompt changes must be evaluated against this frozen rubric; any change to the rubric itself requires a new `annotation-rubric-v3` identifier and a fresh freeze.
