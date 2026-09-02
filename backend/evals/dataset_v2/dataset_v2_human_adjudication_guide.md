# Dataset V2 — Human Adjudication Guide (FROZEN rubric `annotation-rubric-v2`)

**This rubric is frozen.** It is carried forward verbatim-in-intent from the Dataset V1
`job_match_annotation_pilot_v1_guide.md` and `job_match_annotation_pilot_v2_guide.md`
(rubric freeze commits `9e09c7b` / `7f5c77a`). **Do not change any rule after seeing
Dataset V2 model predictions.** No Round 2C, no new examples derived from V2 failures,
no taxonomy V3.

Ground Truth for Dataset V2 must be created **independently of the finalist matchers**.
Do **not** run `qwen3.8-max` or `kimi-k3` before the Ground Truth freeze. The finalist
matcher output must never be used to construct labels.

Allowed evidence: only the **same frozen candidate evidence snapshot** used for Dataset V1
pilot v2 (`resume_extracted`, `manual_confirmed`, confirmed job-seeker identity /
structured candidate facts), same `resume_hash` / `experience_bank_hash`. Forbidden:
`manual_unconfirmed`, `unknown`, AI-inferred facts, conversation memory, common sense,
external information.

---

## 1. Requirement Taxonomy V2 (four types — classify by **Evidence Verifiability**, not keywords)

Ask of every canonical requirement: *"Can this be reasonably and stably verified from the
allowed candidate evidence?"*

| type | meaning | labelling |
|---|---|---|
| **eligibility** | explicit qualification / blocking gate — degree, graduation cohort, minimum years, certification, work authorization, mandatory language, "can intern ≥ N months" future-availability gate | `ai_eligibility_status ∈ {Supported, PotentialGap, Unknown}`; `score_included = false`; **no** Strong/Partial/Missing; `eligibility_category ∈ {degree, graduation_cohort, experience_years, certification, work_authorization, language, other}` |
| **matchable** | a capability / experience a résumé can reasonably verify — AI product experience, Agent delivery, RAG implementation, SQL, data analysis, industry experience, growth, cross-functional delivery | `ai_match_label ∈ {Strong, Partial, Missing}`; `ai_evidence_ids` (≥1 for Strong/Partial, empty for Missing); `ai_grounding_reason` (one sentence, not a restatement); `score_included = true` |
| **knowledge** | mainly theoretical understanding / principles / mechanisms / architecture concepts / capability boundaries — "understand RAG principles", "understand Agent architecture", "understand LLM inference optimization" | `ai_match_label = N/A`; `ai_evidence_ids = []` (must be empty); `knowledge_topics`, `knowledge_text`; `score_included = false` — interview-prep only, never a Gap, never drives résumé rewrite |
| **subjective** | attitude / passion / willingness — "extremely passionate about AI", "strong willingness to learn" | not scored; kept as non-scoring context only |

Only **matchable** enters the Phase 3 semantic matcher and the Match Score (numerator and
denominator). eligibility is checked in a separate "job qualification" area; knowledge is
shown as separate "preparation topics".

## 2. Requirement boundary / compound split

A requirement must be independently judgeable. Split a sentence **only when** the source JD
explicitly supports multiple independently-judgeable requirements, each traceable to
explicit JD text. Do not over-split a natural combination of one capability.

- "有 Agent 产品经验，并深入理解 Agent 架构" → matchable (Agent product experience) + knowledge (Agent architecture understanding).
- "本科及以上学历，计算机、人工智能等相关专业优先" → eligibility (degree gate) + matchable Preferred (major preference).
- "3 年以上 AI 产品经验" → eligibility (`experience_years`) only — do **not** also mint a synonymous matchable.

Never fabricate: do not infer "has Agent project experience" from "understands Agent principles".
Do not infer candidate eligibility from job responsibilities. Do not add implicit gates the JD
does not state.

## 3. Importance — Critical / Important / Preferred

- **Critical**: explicit blocking gate (minimum degree, minimum years, explicit language/qualification).
  Not "sounds important".
- **Important**: core capability / knowledge / experience needed to do the job well.
- **Preferred**: JD explicitly writes 优先 / 加分 / preferred / plus.

## 4. eligibility labels

- **Supported**: verified fact meets the gate.
- **PotentialGap**: verified fact **explicitly conflicts** with the gate (e.g. verified degree
  below requirement; new-grad status vs explicit multi-year professional requirement).
- **Unknown**: current evidence insufficient to confirm, **no explicit conflict**. Missing
  evidence ≠ not satisfied — do not auto-assign PotentialGap for absence.

Years gates use eligibility semantics, never Phase 3 Partial. Do not convert projects /
internships into professional years.

## 5. matchable labels — Strong / Partial / Missing

- **Strong**: verified evidence directly and sufficiently supports the requirement at the level asked.
- **Partial**: relevant evidence, but only partial coverage / adjacent direction / weaker
  depth or scope / missing the required duration or specialisation.
- **Missing**: no usable verified supporting evidence. **Missing ≠ the candidate cannot do
  it** — only that the frozen evidence has no supporting fact.

## 6. Evidence grounding

Every Strong / Partial cites ≥ 1 stable `evidence_id` and one sentence explaining how the
evidence connects to the requirement (not a restatement). Missing keeps evidence IDs empty
and states what kind of verified support is currently absent.

## 7. Canonical Requirement ID

`requirement_id = RequirementCatalogBuilder.stable_requirement_id(source_text,
normalized_requirement, requirement_type, source_section)` → `reqv2_<16hex>`
(SHA-256 prefix of `(NFKC-casefold(source_text), NFKC-casefold(normalized_requirement),
requirement_type, source_section, 0)`; independent of order / importance / label).
If a reviewer edits `source_text` / `normalized_requirement` / `requirement_type` /
`source_section`, note it in `human_notes` and recompute the ID with the same function.

## 8. Human Match Fit (job level, 1–5, human only)

Exact frozen question:

> "Ignoring recruitment eligibility barriers, job type, and personal application
> preference, considering only the candidate's currently verified experiences, skills,
> and the job's matchable requirements, how well does the candidate's capability fit
> this job?"

Do not use any model score while assigning HMF. Reference ceiling from V1:
Spearman(GT score, HMF) = 0.845.

## 9. Overall Fit 1–5 (job level, human only, kept blank until adjudication)

5 Very Strong · 4 Good · 3 Mixed/Plausible · 2 Low · 1 Clearly Unsuitable.
Never mechanically derived from Match Score or any formula.

## 10. ACCEPT / EDIT / REJECT

Per requirement, after reviewing the `ai_*` suggestions:

1. **ACCEPT** — suggestion fully acceptable → fill the matching `human_*` fields, `review_status = accepted`.
2. **EDIT** — taxonomy / granularity / importance / label / evidence / topics need change →
   fill revised `human_*` (`human_taxonomy_decision`, `human_match_label` or
   `human_eligibility_status`, `human_evidence_ids`, `human_grounding_reason`, `human_edit`),
   `review_status = edited`.
3. **REJECT** — requirement should not exist / suggestion unusable → `human_accept_reject = reject`,
   explain in `human_notes`, `review_status = rejected`.

Never overwrite the `ai_*` fields — preserve the audit trail between suggestion and human result.

## 11. Freeze discipline

Dataset V2 Ground Truth is frozen **before** any finalist model is run. After freeze:
run `qwen3.8-max + job-fit-v3-rubric-refined-v2` (primary) and
`kimi-k3 + job-fit-v3-matchable-only` (secondary) once each, join on `requirement_id`,
and report generalisation vs the Dataset V1 development numbers. The rubric does not change
in response to those results.
