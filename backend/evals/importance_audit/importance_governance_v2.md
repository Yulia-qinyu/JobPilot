# Importance & Eligibility Governance (v2) — eval documentation

Recorded 2026-09-02T03:19:28.316783+00:00. Governance/documentation only. No product code, no Match Score weights, no
UI, no frozen dataset changed by this record.

## 1. Eligibility and Capability Match are SEPARATE decision layers

**A. Eligibility** answers: *"Can the candidate apply / satisfy explicit recruiting
qualification gates?"* — graduation cohort, degree, explicit years-of-experience gate,
required certificate/licence, explicit language requirement.
Statuses: `Supported` / `PotentialGap` / `Unknown` (plus explicit blocker / `Ineligible`
where the deterministic eligibility layer already supports it).
**Eligibility requirements DO NOT enter Match Score.** Do **not** convert eligibility
requirements into Match-Score Critical items. A candidate may legitimately have
`Capability Match Score = high` while `Eligibility = Ineligible / PotentialGap`. This is intentional.

**B. Matchable requirements** answer: *"How strongly does the candidate's verified career
evidence cover the capabilities needed to perform the role?"* Only matchable requirements
enter Match Score. Matchable Importance may legitimately be **Critical / Important /
Preferred** — **Critical is NOT reserved for eligibility.** Dataset V1 currently having
**0 Critical matchable requirements** is an annotation-governance finding, not a product rule.

**C. Knowledge** requirements remain non-Match-Score preparation / interview-readiness topics.

**D. Subjective** expectations remain context-only, non-scoring.

## 2. Importance semantics (JOB-SIDE judgment — never use candidate strength/weakness)

- **Critical** — a core capability whose absence would materially prevent or seriously
  impair the candidate from performing the main responsibilities of the role.
  *Human test:* "If the candidate completely lacked this capability, could they still
  reasonably perform the core job?" If essentially no → Critical may be appropriate.
- **Important** — a substantial capability that meaningfully affects success and
  performance but is not the defining/core blocker. If absent, the candidate could still
  perform the role, but with a meaningful capability gap.
- **Preferred** — a genuine bonus / nice-to-have; its absence should not materially
  undermine ability to perform the core job.

Do **not** classify by keywords alone. 核心 / 负责 / 主导 / 独立 / 优先 / 加分 and
years/seniority language are **evidence/context, not deterministic labels**. Role context
and responsibility centrality control.

## 3. Importance uncertainty

Human review may record `importance_uncertain = true|false`. Use `true` when: Critical vs
Important stays genuinely debatable after full JD context; the JD wording does not make
centrality clear; or the requirement bundles multiple capabilities of differing centrality.
**No fourth score weight.** The finally frozen importance is still one of Critical /
Important / Preferred; the flag exists only for adjudication/governance.

## 4. Match Score is unchanged

Deterministic scoring stays: weight `{Critical:5, Important:3, Preferred:1}`; multiplier
`{Strong:1, Partial:0.5, Missing:0}`; **only matchable** requirements in numerator and
denominator; **eligibility never enters the score.**

The previously reported **Spearman(GT Match Score, Human Match Fit) = 0.845** is now
described as **"provisionally supported / pre-Importance-audit construct validity"** until
high-impact Importance labels get explicit human review and the correlation is recomputed.
**Do not recompute final construct-validity metrics yet.**

## 6. Compound (A AND B) requirement human rule

Do **not** use "weakest subclaim mechanically determines the whole label" as a universal rule.

- **Strong** — all material subclaims are sufficiently supported.
- **Partial** — one or more material subclaims have meaningful evidence, but the complete
  compound capability is materially incomplete.
- **Missing** — no meaningful evidence for the core compound capability, or the supported
  portion is only incidental/adjacent and does not demonstrate the actual requested capability.

Human judgment must weigh: semantic centrality of each subclaim; whether the supported
subclaim is itself a material part of the requirement; whether the missing component
fundamentally changes the capability. The already-adjudicated **F01–F05 remain Partial**.

## 11. Intended product presentation (documentation only — NO UI change in this task)

Present Capability Match and Eligibility as distinct signals, e.g.:

> Capability Match: 86
> Eligibility: Potential Gap / Ineligible
> "Your verified capabilities align strongly with this role, but an explicit recruiting
> qualification may not be satisfied."

Do not implement UI changes; do not modify frontend. Documentation only.
