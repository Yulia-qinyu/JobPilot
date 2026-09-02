# Importance (Critical / Important / Preferred) — Human Review Guide

Applies to Dataset V1 GT importance re-audit AND the Synthetic Challenge Set probes.
This does not change Match Score weights (Critical 5 / Important 3 / Preferred 1) or any
label automatically. It records an explicit, auditable human importance decision.

## Semantics (decide from the JOB side only)

- **Critical** — a core requirement whose ABSENCE materially undermines the candidate's
  ability to perform the main role. Typically an explicit blocking gate (minimum degree,
  minimum years, mandatory qualification/language) OR the single defining capability the
  role is built around, stated as required.
- **Important** — a meaningful requirement that contributes substantially to success but
  is not the defining/core capability of the role.
- **Preferred** — a genuine advantage / bonus / nice-to-have; its absence should not
  heavily penalise fit. JD wording like 优先 / 加分 / preferred / plus.

## Rules

1. **Job-side only.** Decide importance from the role's core work + responsibility
   centrality + JD wording. **Do NOT** use how strong the candidate's evidence is.
2. **No keyword-only classification.** 优先/加分 usually ⇒ Preferred, but confirm against
   context. 负责/核心 suggests centrality but is not automatic Critical.
3. **Role context matters.** "熟悉 SQL" may be Important for a general PM but Critical for a
   data-product role whose core work is SQL-driven.
4. **Years / seniority language** ("3年以上", "资深", "独立负责") on an *eligibility*
   requirement ⇒ usually Critical (blocking gate). On a *matchable* requirement, judge
   whether the JD makes it the defining capability (Critical) or one of several
   contributors (Important).
5. **Eligibility importance** still gets a decision, but remember eligibility does not
   enter Match Score — its weight only matters if the taxonomy of the row is later revised.
6. Record: `human_importance` ∈ {Critical, Important, Preferred}, `importance_review_status`
   ∈ {pending, accepted, edited}, and a one-line `*_notes` citing the JD phrase you used.

## Worked examples

- "有金融行业经验优先" → **Preferred** (explicit 优先, non-blocking).
- "负责核心 RAG 产品设计，需有生产级 RAG 经验" → may be **Critical** (defining capability,
  stated as required).
- "熟悉 SQL" for a general PM → likely **Important**; for a data-product PM whose core
  work is SQL/data-modelling → potentially **Critical**.
- "本科及以上学历" → **Critical** eligibility gate (blocking).
- "有 A/B 实验设计经验" as one of several analytical skills → likely **Important**; if the
  role IS an experimentation-platform PM → **Critical**.

## Priority order for the V1 re-audit

1. matchable + high Important↔Preferred Match-Score sensitivity (see
   `importance_audit_v1_sensitivity.*`).
2. matchable Missing/Partial rows in small (≤3 matchable) jobs.
3. rows with 优先/加分 currently NOT marked Preferred, or 负责/核心/年以上 NOT marked
   Critical/Important consistently.
4. everything else.
