# Prompt Refinement Round 2B — Prompt Diff (A vs B vs C)

| | id | added chars vs control | sha256 (instruction block) |
|---|---|---|---|
| PROMPT_A / control | `job-fit-v3-matchable-only` | 0 | `abacf2cffd27d596cc55d9113a7dd70f8a176e6c414521ecd36904410c2f37ad` |
| PROMPT_B / rejected | `job-fit-v3-rubric-aligned-v1` | 3442 | `4ff452b969b8d82c45c1ddf8c9fc8281b9de5822b9068dfead9b1a923dcafc3a` |
| PROMPT_C / refined | `job-fit-v3-rubric-refined-v2` | 1808 | `7625ac3759eaa329a21dee1eb7665f3cc1f0f8cd083458846b7bf7eaeaac1196` |
| production `requirement_matcher.py` | (unchanged) | — | `e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b` |

Prompt C base byte-identical to control outside the single insert: **True**

## UNCHANGED in C (vs control)
- All `job-fit-v3-matchable-only` semantic instructions, Section D output contract, evidence
  rules, output schema, requirement taxonomy, label set, and the JOB REQUIREMENTS / EVIDENCE
  payloads. Transport, reasoning mode, temperature, max_tokens, normalization, MatchScoreService,
  join key, metrics.

## KEPT from Prompt B (3 of 5 rule groups, compacted)
- **A. Technology Adjacency** — adjacent tech is not automatic Partial; general AI/LLM/RAG is
  not automatic credit for multimodal / ASR / RL-training / fine-tuning / training-infra /
  specialised rec-search; general-or-neighbouring-only → Missing.
- **B. Project vs Formal Work** — complete project can support Strong for practical /
  implementation / delivery / productisation / hands-on requirements; when formal
  professional-role experience / job-function years / seniority / tenure / ownership scope is
  explicitly requested, project alone is not equivalent — Partial at most.
- **C. Label Calibration** — Strong = direct sufficiently-complete at the requested level;
  Partial = meaningful but materially incomplete; Missing = no meaningful or only
  general/adjacent evidence; Partial not for uncertainty.

## REMOVED from Prompt B
- **OR / alternative-list rule** — Round 2A: Sonnet improved substantially, qwen3.8-max only
  modestly, **kimi-k3 materially regressed on the OR-list slice**. Finalists are kimi-k3 and
  qwen3.8-max; Prompt C is not optimised for Sonnet. REMOVED.
- **Compound requirement / narrowest-unmet-subclaim rule** — Round 2A: the compound slice
  **regressed for all three tested models**. Rejected in its current wording. REMOVED.

## NO new rules, NO examples, NO few-shot, NO Dataset V1 cases, NO Ground Truth. Prompt C is a
REDUCTION of Prompt B, not another expansion.
