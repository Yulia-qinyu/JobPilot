# Prompt Ablation Round 2A — Prompt Diff (audit)

| | value |
|---|---|
| prompt_control | `job-fit-v3-matchable-only` |
| prompt_treatment | `job-fit-v3-rubric-aligned-v1` (eval-only) |
| control instruction-block sha256 | `abacf2cffd27d596cc55d9113a7dd70f8a176e6c414521ecd36904410c2f37ad` |
| treatment instruction-block sha256 | `4ff452b969b8d82c45c1ddf8c9fc8281b9de5822b9068dfead9b1a923dcafc3a` |
| production `requirement_matcher.py` sha256 | `e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b` (UNCHANGED) |
| added characters | 3442 |
| base byte-identical outside the single insert | True |

## UNCHANGED
- All current `job-fit-v3-matchable-only` semantic instructions (matcher role, MATCH RULES,
  IMPORTANCE, HARD REQUIREMENTS, OUTPUT), verbatim.
- Section D output contract (`summary` / `requirement_matches[{requirement_id, match_label,
  evidence_ids, reason}]` / `suggested_preparation`).
- Evidence rules, output schema, requirement taxonomy, label set {Strong, Partial, Missing}.
- The `JOB REQUIREMENTS:` and `ELIGIBLE CANDIDATE EVIDENCE:` payloads (byte-identical).
- Transport, reasoning mode, temperature policy, max_tokens, normalization, MatchScoreService,
  join key, metrics.

## ADDED ONLY — one block: `ADJUDICATION RULES (rubric-aligned v1)`, before `IMPORTANCE:`
1. OR / alternative-list semantics (branches are alternatives unless wording requires all;
   independent qualifiers — years, proficiency, ownership scope, formal work experience,
   seniority, domain depth — still apply).
2. Technology-adjacency guardrail (adjacent tech is not automatic Partial; general LLM/RAG/AI
   is not automatic credit for multimodal / ASR / RL-training / fine-tuning / training infra /
   specialised rec-search; Partial needs materially overlapping evidence; else Missing).
3. Project vs formal work experience (a complete project can support Strong for
   direction/productisation/implementation/delivery requirements; project alone usually cannot
   support Strong when formal professional-role experience / job-function years / seniority /
   tenure / full professional ownership is explicitly requested — Partial at most).
4. Compound requirement / narrowest unmet subclaim (judge against the least-supported material
   subclaim; A AND B needs both strong for Strong; one partial subclaim -> Partial; an
   unsupported material subclaim -> possibly Missing; do not split the row).
5. Explicit Strong / Partial / Missing calibration (Strong = direct sufficiently-complete
   evidence at the requested level; Partial = meaningful but incomplete; Missing = lacking or
   only general/adjacent evidence; Partial must not be a generic uncertainty bucket).

The added block contains NO Ground-Truth labels, NO Human Match Fit, NO Dataset V1 job/requirement ids, NO baseline wrong predictions, NO per-model failure examples, NO score deltas, NO benchmark rankings, NO company/title heuristics. The rules are generic re-statements of the frozen human adjudication rubric.
