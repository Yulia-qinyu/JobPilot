# Dataset V1 Importance Audit — Summary

## A. Was Critical / Important / Preferred explicitly human-reviewed in Dataset V1 GT?

**No.** Importance labels were assigned during pre-annotation (under `annotation-rubric-v2`, no LLM call, no production matcher) and carried through the human ACCEPT/EDIT/REJECT pass **without an explicit per-requirement importance decision**.

### Evidence
- Annotation schema has NO human_importance field (schema keys: ['ai_eligibility_status', 'ai_evidence_ids', 'ai_grounding_reason', 'ai_match_label', 'company', 'eligibility_category', 'human_accept_reject', 'human_edit', 'human_eligibility_status', 'human_evidence_ids', 'human_grounding_reason', 'human_match_label', 'human_notes', 'human_taxonomy_decision', 'importance', 'job_id', 'job_title', 'knowledge_text', 'knowledge_topics', 'needs_human_review', 'normalized_requirement', 'pilot_reference', 'requirement_id', 'requirement_type', 'review_status', 'score_included', 'source_section', 'source_text', 'v1_ref']); the only human decision fields are human_taxonomy_decision / human_match_label / human_eligibility_status / human_evidence_ids / human_grounding_reason / human_edit / human_accept_reject / human_notes.
- Importance distribution is identical between AI pre-annotation and human-verified: pre {'Critical': 42, 'Important': 78, 'Preferred': 38} vs verified {'Critical': 42, 'Important': 78, 'Preferred': 38}.
- 0 of 158 requirements have any importance-value difference between pre-annotation and human-verified (i.e. none).
- changes[] trail entries touch human_match_label, human_eligibility_status, human_notes, human_match_fit (30 job-level), subjective_expectations[+], and rule-record fields — NEVER importance (importance_touched_in_changes=False).
- Pilot-10 rows carry a v1_ref tag like 'R01(Critical/Partial)' — importance was set at Pilot V1 time and some values were cited as examples in the frozen rubric guide (§2), i.e. rubric-development scrutiny, but still not a structured per-row importance ACCEPT in any pass.
- full_review_edits F1-F4 are all human_match_label (Partial<->Strong); none touch importance.
- provenance: 'New 20 = accept AI pre-annotation except edits F1-F4' — importance accepted as part of the bulk pre-annotation, not per-row reviewed.
- freeze_note lists protected fields; importance is not among them and was not itself reviewed.
- Rubric guides DO define Critical/Important/Preferred semantics (pilot v1 §2, pilot v2 §3) and EDIT instructions list 'importance' as adjustable — but the artifact shows zero importance adjustments and provides no field to record an importance ACCEPT.

## Counts

- Total canonical requirements: **158**
- Importance distribution (identical AI pre-annotation ↔ human-verified): **Critical 42 / Important 78 / Preferred 38**
- By type:
  - eligibility: {'Critical': 42}
  - matchable: {'Important': 63, 'Preferred': 37}  ← Match-Score-bearing
  - knowledge: {'Important': 15, 'Preferred': 1}

- **importance_explicitly_human_verified: 0**
- **importance_not_explicitly_human_verified: 158**
- **importance_provenance_unknown: 0** (provenance documented for all)

> Note: **every Critical label in V1 GT is on an `eligibility` requirement. Zero `matchable` requirements are Critical.** Match Score is computed over matchable requirements only, so the realistic importance-mislabel risk for scoring is **Important ↔ Preferred** (weights 3 ↔ 1).
