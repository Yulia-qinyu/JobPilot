# Dataset V2-Real — Source Provenance & Text Fidelity Policy (revised)

**Type:** evaluation-dataset governance. Not a product/prompt/taxonomy/model change.
**Supersedes:** the earlier binary rule ("if automated re-capture cannot prove verbatim
fidelity, the job cannot enter V2-Real").

Dataset V2 is a **human-curated real-world held-out** evaluation set. The human evaluator
is permitted to be the **provenance authority** for JDs they manually copied from real
recruiting pages. Automated page re-capture is **not** required for every job.

## Why automated verbatim re-capture is no longer mandatory

- The evaluation environment cannot reliably reach mainland-China recruiting SPAs
  (browser navigation to talent.baidu.com / zhaopin.jd.com / careers.tencent.com was
  denied; Lever returned 403). Requiring machine re-capture would make a real held-out
  set impossible to build here.
- `WebFetch` "re-capture" is itself **model-rendered**, i.e. *lower* fidelity than a
  careful human copy-paste — it is not a gold standard to gate against.
- Provenance ("is this a real posting from a real employer?") and literal text fidelity
  ("is every character byte-identical to the source?") are **different questions**. A
  human who copied the text from the live page can attest to provenance even when the URL
  is no longer recoverable.
- The integrity risks that actually matter for a held-out set — **synthetic generation**
  and **semantic rewriting** — are controlled by explicit rules below and by the raw-text
  audit trail, not by machine re-capture.

## 1. Three-level source verification

### LEVEL A — `source_verified`  (`real_world_verified = true`)
All of: real posting · identifiable employer · identifiable job title · source URL or
stable source identifier available · human-captured raw JD **or** source-retrieved raw JD ·
no semantic rewriting.

### LEVEL B — `human_provenance_verified`  (`real_world_verified = true`)
All of: the human evaluator **explicitly confirms** the JD was manually copied from a real
recruiting/job-posting page · raw pasted text preserved · not synthetically generated ·
no semantic rewriting · obvious-mojibake cleanup separately audited.
Source URL **may be missing/unrecoverable** → set `source_url_missing = true`.

### LEVEL C — `unverified`  (`real_world_verified = false`)
Origin cannot be reliably established, or the evaluator cannot confirm a real posting, or
the text may be reconstructed / generated / materially modified.
**LEVEL C must not enter the frozen V2-Real corpus.**

## 2. JD text fidelity (recorded separately from provenance)

`job_description_raw` (verbatim, never mutated) + `job_description_cleaned`.
`jd_text_fidelity` ∈:

| value | meaning |
|---|---|
| `human_captured_raw` | human copy-paste; no corruption removed (whitespace/line-break tidy only) |
| `source_retrieved_raw` | pulled from the live source page as raw text |
| `cleaned_corruption_only` | human copy-paste; only mojibake / unrecoverable fragments removed, audited in the cleanup report |
| `model_rendered_unverified` | obtained via a model-rendered fetch (e.g. WebFetch); not verbatim |

A job does **not** become synthetic because corrupted characters were removed
conservatively.

## 3. Cleaning policy (unchanged)

Allowed: delete obvious mojibake · remove unrecoverable corrupted fragments (whole
sentence if semantically unreliable) · whitespace normalization.
Not allowed: reconstruct missing words · paraphrase · rewrite · translate · add inferred
requirements. Raw text always preserved; every removal logged in
`dataset_v2_batch*_cleanup_report.json`.

## 4. Batch 1 vs Batch 2 are different provenance classes

- **Batch 2** (16 human-pasted): the evaluator confirms manual copy from real postings →
  eligible for **LEVEL B** `human_provenance_verified`, subject to integrity review.
- **Batch 1** (10 WebFetch-rendered): remain `unverified` / `model_rendered_unverified`
  **unless** the source URL can be verified **and** sufficient original source content is
  available. Do **not** auto-promote Batch 1 merely because a URL exists.

## 5. V2-Real corpus eligibility

A job may enter V2-Real when **all** hold:
1. `real_world_verified = true` (LEVEL A or LEVEL B), and
2. not a Dataset V1 duplicate, and
3. the JD contains enough intact semantic content for requirement annotation, and
4. it passes final human review.

`source_verified` and `human_provenance_verified` are both eligible. `unverified` is not.
"Eligible" ≠ "in the corpus": promotion into `dataset_v2_jobs.json` is a deliberate human
step at freeze time.

## 6. Quantity language

`candidate_count` (anything staged) is **not** `verified_real_corpus_count`
(LEVEL A/B, deduped, annotation-ready, human-reviewed).
**The V2-Real minimum is not met just because candidate_count ≥ 24.**

- Preferred V2-Real: **30 verified real Chinese jobs**
- Minimum acceptable: **24 verified real Chinese jobs**
