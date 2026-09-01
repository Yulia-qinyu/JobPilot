# JobPilot Full 30-JD Ground Truth V2 — Human Verified / FROZEN

## Status

| field | value |
|---|---|
| `artifact_type` | `human_verified_ground_truth` |
| `status` | `full_30_human_verified_v2` |
| `dataset` | `job_match_eval_dataset_v1` |
| `rubric_id` | `annotation-rubric-v2` (`rubric_freeze_state: frozen`) |
| `review_complete` | `true` |
| `human_match_fit_jobs` | **30 / 30** |
| `evaluation_join_key` | `["job_id", "requirement_id"]` |
| `ground_truth_version` | `job-match-ground-truth-v2` |
| `freeze_state` | `frozen` (final integrity review passed 2026-09-01) |
| `ground_truth_frozen_id` | `job-match-ground-truth-v2` |
| `ground_truth_frozen_on` | `2026-09-01` |
| milestone commits | product `9e09c7b` · rubric freeze `7f5c77a` |

Human adjudication applied mechanically to the Full V2 pre-annotation. `ai_*` fields are immutable and preserved verbatim (including rows where Human ≠ AI). Pilot 10 human decisions copied verbatim from the frozen Pilot V2 human-verified artifact. New 20 = accept AI pre-annotation except edits F1–F4. `duplicate_ordinal` workaround removed. **No Claude call, no production matcher, no baseline, no model benchmark, no evaluation metrics, no Match Score, no DB/app/profile/rubric mutation.**

## 1. 30 Jobs — confirmed

All 30 Dataset V1 jobs, in dataset order, exact canonical IDs (verified). 10 `pilot_reference: true`, 20 `pilot_reference: false`.

## 2. Final Canonical Requirement Count

**158** (65 pilot + 93 new). After removing the `duplicate_ordinal` workaround the count is unchanged — only one row's `requirement_id` was restored. **17 → 19 subjective expectations** (17 pre-annotation + 1 pilot EDIT-A carried + 1 EDIT-F1 addition).

## 3. Final Taxonomy Distribution (158)

| type | count | in Match Score |
|---|---|---|
| eligibility | **42** | no |
| matchable | **100** | yes |
| knowledge | **16** | no |
| subjective expectation (separate) | **19** | no |

Unchanged from pre-annotation (no taxonomy reclassification in Full review; F1–F4 change labels only).

## 4. Final Human Matchable Label Distribution (100)

| label | AI pre-annotation | **Human GT** | delta |
|---|---|---|---|
| Strong | 52 | **52** | −2 pilot (B,D,E) + F1 + F3 + F4 − F2 |
| Partial | 31 | **30** | +1 pilot (D,E in / B out) + F2 − F1 − F3 − F4 |
| Missing | 17 | **18** | +1 pilot (B) |

## 5. Final Human Eligibility Status Distribution (42)

| status | AI pre-annotation | **Human GT** | delta |
|---|---|---|---|
| Supported | 22 | **23** | +1 (pilot EDIT C: Unknown→Supported) |
| PotentialGap | 16 | **16** | — |
| Unknown | 4 | **3** | −1 (pilot EDIT C) |

## 6. Final Subjective Count

**19** subjective expectations, all `scored: false`, all `human_keep_as_context: keep`. New in Full review: `文字品味` (from EDIT F1). Carried from frozen pilot: `独立、主动的学习能力` (Pilot EDIT A).

## 7. Accepted Requirement Count — **149**
## 8. Edited Requirement Count — **9** (5 pilot frozen edits B–E + A-labelled row; 4 Full-review edits F1–F4)
## 9. Rejected Count — **0**

*(Pilot breakdown carried verbatim: 60 accepted + 5 edited. New-20: 89 accepted + 4 edited. `review_status = edited` only where Human ≠ AI or structure materially changed.)*

## 10. All Full-Review Edits

| edit | requirement_id | job | type | AI → **Human** | rationale |
|---|---|---|---|---|---|
| **F1** | `reqv2_63b051ca5b06efc5` | 百度 AI产品经理（J84492） | matchable | Partial → **Strong** | 业务分析 / 数据洞察 / 客户反馈直接支持洞察与规律总结能力；同句“文字品味”是不可稳定验证的主观审美，不应压低可验证能力标签。**新增 subjective “文字品味”（非评分）。** |
| **F2** | `reqv2_f7ca00a2f542fb78` | 百度 大模型应用平台产品经理（J85776） | matchable | Strong → **Partial** | 需求抽象 / 客户场景 / 产品流程有直接证据，但该复合要求还要求“熟练使用产品经理相关工具”，冻结证据无工具使用事实，覆盖不完整。 |
| **F3** | `reqv2_9149c4b1d212048c` | 腾讯 QQ-Agent产品经理 | matchable | Partial → **Strong** | OR-list：JD 为 AI Agent / 大模型应用 / 智能助手类产品经验的可替代方向；GoFin 的 LLM / 对话式 Agent 产品化落地满足其一，不因未覆盖全部而降级。 |
| **F4** | `reqv2_23a50d8ef3c57335` | 腾讯会议 评测产品经理 | matchable | Partial → **Strong** | OR-list：候选人大模型与智能对话产品实践直接覆盖明确允许方向之一；未覆盖 ASR / AI 搜索 / 语音助手不自动降级。 |

Explicit KEEP-as-is decisions (reviewed, no label change): **K1** `reqv2_5cfb41f2e516a713` (1年经验优先 → matchable/Preferred/Partial); **K2** `reqv2_91500289fe78e7b4` (数据开发/SQL → matchable/Partial); **K3** `reqv2_8fde0b9d53173e67` (模型任务目标/效果标准 → matchable/Partial); **K4** Xsolla builder-culture row → matchable/Partial; **K5** `硕士及以上学历优先` → matchable/Preferred/Strong (edge case, no rubric change); **K6** 百度 J72652 two knowledge rows kept separate; **§8** `reqv2_379e8bc24f903143` (微信输入法 C 端 AI 产品 → **Strong**, kept); **§11** `reqv2_2a8d6b3110257858` (AI/策略/评测产品经验 → **Partial**, not upgraded); **§9** 百度 J85776 “AI 平台类或 B 端” + 腾讯光子 “B端/数据/AI平台” → **Partial** (kept, not Missing).

## 11. Pilot Human Decisions — Preserved

The 10 pilot jobs' requirement-level human taxonomy, `human_match_label` / `human_eligibility_status`, `human_evidence_ids`, `human_grounding_reason`, `human_edit`, `human_notes`, `review_status`, subjective decisions (incl. the EDIT-A `独立、主动的学习能力` addition), and `human_match_fit` are copied **verbatim** from `job_match_annotation_pilot_v2_human_verified.json`. Validated: **0 drift** across all 65 pilot rows and all 10 pilot `human_match_fit` values. Not re-adjudicated.

## 12. GoFin C-End Manual Confirmation

Candidate human-confirmed during adjudication that **GoFin is a C-end / consumer-facing product**. Recorded **only** in `human_grounding_reason` / `human_notes` on `reqv2_379e8bc24f903143` (微信输入法 "C 端 AI 产品经验"), which is kept at **Human = Strong**. No evidence ID created, no Candidate Profile change, no frozen-snapshot mutation, not propagated as `ai_*` evidence. Listed in `manual_ground_truth_facts`.

## 13. GoFin AI-Platform Manual Confirmation

Candidate human-confirmed that **GoFin is also an AI platform**. Recorded **only** in `human_notes` on the two AI-platform / B-end rows — `百度 J85776` "AI 平台类或 B 端产品经验" and `腾讯 光子` "B端 / 数据 / AI / 研发效能平台…" — both kept at **Human = Partial** (GoFin supports the AI-platform direction but is project-based, not long-term formal platform-PM work; therefore not Missing, not Strong). No evidence ID, no snapshot/profile mutation.

## 14. Project Experience vs Work Experience — Adjudication Rule Recorded

Recorded in `adjudication_rules.project_vs_work_experience`: *Project experience can count as matchable evidence. When JD semantics clearly imply a formal role / professional work experience, a project alone normally supports **Partial**, not automatic Strong (e.g. `腾讯会议 评测 "AI / 策略 / 评测产品相关经验"` kept Partial). When JD asks only for related-direction / delivery / productization experience, a sufficiently direct and complete project may support **Strong** (e.g. F3, F4).* **Not** a Rubric V2 modification — application guideline only.

## 15. OR / Alternative-List — Adjudication Rule Recorded

Recorded in `adjudication_rules.or_alternative_list`: *When a JD explicitly lists alternative acceptable directions (OR / 之一 / 等方向), meeting one clearly permitted alternative is not downgraded merely because other listed alternatives are absent (F3 QQ-Agent, F4 Tencent Meeting). This does not erase extra qualifiers — formal work experience, years, proficiency/depth, C-end/B-end, ownership/measurable outcomes.* **Not** a Rubric V2 modification.

## 16. Baidu J72652 — Two Knowledge Rows Remain Separate

`对大模型底层技术有一定理解` and `对大模型有基本了解` are kept as **two distinct knowledge / non-scoring rows** (different depth/semantics: baseline understanding vs deeper technical-understanding preference). Their pre-annotation ambiguity flag is resolved. Recorded in `adjudication_rules.j72652_two_knowledge_rows`.

## 17. Canonical Evaluation Join Key

`evaluation_join_key = ["job_id", "requirement_id"]`. `requirement_id` is canonical/stable **within its job context**; two different jobs are allowed to produce the same deterministic `requirement_id`. Global uniqueness of `requirement_id` alone is **not** required and **not** enforced. Uniqueness is enforced on the **`(job_id, requirement_id)` pair** — validated: all 158 pairs unique. Downstream Ground-Truth-vs-prediction reconciliation and benchmark joins must use `(job_id, requirement_id)`; no fuzzy/text join is required.

## 18. `duplicate_ordinal` Workaround Removed

The pre-annotation had assigned `tencent:2013806539382611968` "三年以上工作经验" a synthetic id `reqv2_1a525cde503f66d0` via `duplicate_ordinal=1`. This is removed. The id is restored to the **exact** value `RequirementCatalogBuilder.stable_requirement_id(source_text="三年以上工作经验", normalized_requirement="三年以上工作经验", requirement_type="eligibility", source_section="experience")` naturally produces: **`reqv2_d65a91721a2406a6`**. `RequirementCatalogBuilder` and all product code are unchanged; no evaluation-only ID was invented. All other fields on that row (`ai_*`, `source_text`, …) are unchanged.

## 19. Duplicated `requirement_id` Across Different Jobs After Restoration

Exactly **one**: `reqv2_d65a91721a2406a6` now appears on both
- `tencent:1994013057063473152` (腾讯 企业微信-基础产品经理) — pilot, "三年以上工作经验"
- `tencent:2013806539382611968` (腾讯 大数据产品经理) — new, "三年以上工作经验"

Identical canonical requirement identity → identical deterministic id, by design. The rows remain distinct by `job_id`.

## 20. Proof All `(job_id, requirement_id)` Pairs Unique

158 rows → 158 distinct `(job_id, requirement_id)` pairs (validated: `len(set(pairs)) == len(pairs) == 158`). Distinct bare `requirement_id` values: 157 (one shared across two jobs). `human_verified_statistics.unique_job_requirement_pairs = true`.

## 21. Human Match Fit — 30 Values + Distribution

| order | job | pilot | HMF | | order | job | pilot | HMF |
|---|---|---|---|---|---|---|---|---|
| 1 | Veeva Senior PM - AI Agent | P | 3 | | 16 | SES AI Data Product Manager | N | 2 |
| 2 | 百度 AI 产品经理实习生（J103757） | P | 5 | | 17 | 腾讯 光子 AI-数据平台产品经理 | N | 4 |
| 3 | 百度 AI产品经理（J84006） | N | 3 | | 18 | 腾讯 大数据产品经理 | N | 4 |
| 4 | 百度 AI产品经理（J84492） | N | 3 | | 19 | 腾讯 金融科技-AI数据产品经理 | P | 4 |
| 5 | 百度 AI产品经理（J96736） | N | 4 | | 20 | 百度 产品经理实习生（J104146） | P | 4 |
| 6 | 百度 AI产品经理（J98328） | N | 4 | | 21 | 百度 北京-用户产品经理(J100806) | N | 5 |
| 7 | 百度 北京-AI产品经理(J100665) | N | 5 | | 22 | 腾讯 企业微信-基础产品经理 | P | 4 |
| 8 | 百度 大模型产品经理（J72652） | N | 4 | | 23 | 腾讯云-经营系统产品经理 | N | 2 |
| 9 | 百度 大模型应用平台产品经理（J85776） | N | 4 | | 24 | 腾讯会议-评测产品经理 | N | 4 |
| 10 | 腾讯 AI产品经理 (2092538895714664448) | N | 3 | | 25 | Xsolla AI-First Engineering Intern | N | 3 |
| 11 | 腾讯 AI产品经理-AI平台（Agent）方向 | P | 4 | | 26 | 华为 AI大模型架构师（训练/推理） | P | 2 |
| 12 | 腾讯 QQ-Agent产品经理 | N | 5 | | 27 | 腾讯 微信-语音识别算法工程师 | N | 2 |
| 13 | 腾讯 微信输入法-AI产品经理 | N | 4 | | 28 | 百度 北京-策略产品经理(J100784) | N | 5 |
| 14 | 腾讯 腾讯会议-AI产品经理-ASR方向 | N | 3 | | 29 | 百度 大模型策略产品经理（J97330） | P | 2 |
| 15 | 腾讯 证券-AI产品经理-金融AI应用体验方向 | P | 4 | | 30 | 腾讯 腾讯视频-增长产品经理 | P | 4 |

**Distribution (all 30): 5 → 5 · 4 → 14 · 3 → 6 · 2 → 5 · 1 → 0.**
- Pilot 10 (verbatim from frozen Pilot V2): 5:1 / 4:6 / 3:1 / 2:2.
- New 20 (from Full-review adjudication): 5:4 / 4:8 / 3:5 / 2:3.

Human Match Fit excludes years-of-experience blockers, campus-vs-experienced recruitment type, internship preference, willingness to apply, company/location preference, salary, and formal eligibility blockers. Eligibility is evaluated separately.

## 22. Frozen Candidate Evidence — Unchanged

`candidate_evidence_snapshot` copied byte-identical from the Full V2 pre-annotation (which copied Pilot V2): `catalog_version = candidate-evidence-v2`, `resume_hash = a5c64e17…e4f4f`, `experience_bank_hash = a9639873…affef5`, 30-item catalog, `resume_extracted` / `manual_confirmed` only. Every `human_evidence_ids` value is one of the 30 frozen IDs (validated); no `manual_unconfirmed`; **no evidence item created**. The three manual Ground-Truth facts (GoFin C-end, GoFin AI-platform, Chinese-native) live only in human notes.

## 23. Dataset V1 — Unchanged
`job_match_eval_dataset_v1.json` `3654d64c…b2b558` · `.csv` `5d055805…88d6b`. Read-only.

## 24. Pilot Artifacts — Unchanged
`pilot_v1.json` `0770bbae…b2b58` · `pilot_v1.csv` `bd80b8c6…fef2a` · `pilot_v2.json` `7151e746…7924b` · `pilot_v2_human_verified.json` `33481b14…4c0ef`. All byte-unchanged.

## 25. Full Pre-Annotation — Unchanged
`job_match_annotation_full_v2_preannotation.json` / `.csv` / `_need_human_review.csv` / `_edge_cases.csv` were read-only inputs (mtime unchanged). This task writes only `*_human_verified*` files.

## 26. Annotation Rubric V2 — Unchanged
`annotation-rubric-v2` (`freeze_state: frozen`) consumed read-only. No taxonomy, label semantics, Evidence-Verifiability principle, or Human Match Fit definition modified. The K5 degree-preference edge case and all F/K/§ decisions are recorded as adjudication notes, **not** rubric changes. No V2.1 in this task.

## 27. No Baseline / Benchmark
Claude baseline **0** · production semantic matcher **0** · model comparison/benchmark **0**.

## 28. No Match Score / F1
Match Score computed **0** · precision / recall / F1 / accuracy **0**. (Metrics are explicitly deferred to a later task.) Only deterministic helper used: `RequirementCatalogBuilder.stable_requirement_id` (pure hash, restoring one id).

## 29. No Product Code Change
No file under `backend/app/`, `backend/alembic/`, `frontend/`, or any production schema/service touched. No DB mutation, no Candidate Profile mutation. Only new `backend/evals/*_human_verified*` files added.

## 30. Output Files (new — nothing overwritten)
- `backend/evals/job_match_annotation_full_v2_human_verified.json`
- `backend/evals/job_match_annotation_full_v2_human_verified.csv` (158 requirement rows)
- `backend/evals/job_match_annotation_full_v2_human_verified_report.md` (this file)
- `backend/evals/job_match_annotation_full_v2_human_verified_changes.csv` (54 rows: 30 Human Match Fit + 5 pilot frozen edits carried + 1 pilot subjective carried + 4 Full-review edits + 1 subjective added + 3 keep-with-note + 2 GoFin AI-platform + 1 GoFin C-end + 1 project-vs-work + 1 join-key correction + 5 adjudication notes)

## 31. Next Step

The final integrity review passed on 2026-09-01 and **`job-match-ground-truth-v2` is now frozen** (`freeze_state: frozen`, `ground_truth_frozen_id: job-match-ground-truth-v2`). This was a metadata-only freeze — no AI field, human label, human eligibility status, human evidence id, Human Match Fit value, taxonomy, `source_text`, `normalized_requirement`, subjective expectation, or canonical requirement identity changed. The evaluation pipeline is now cleared for the **Current Claude Baseline** run, followed by model benchmark and evaluation-metric computation (precision / recall / F1 / Match Score correlation) against this Ground Truth using the `(job_id, requirement_id)` join key.
