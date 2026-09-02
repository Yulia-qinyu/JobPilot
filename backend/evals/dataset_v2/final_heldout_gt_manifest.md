# Final Held-Out GT Manifest

_Frozen 2026-09-02T13:17:06.541286+00:00_

| dataset | role |
|---|---|
| Dataset V1 | development / model-selection (NOT held out) |
| Dataset V2-Real | small held-out real-world validation |
| Dataset V2-Synthetic | separate behavioral stress-test |

## V2-Real

- 8 jobs · 32 matchable requirements · **32/32 human labels** · **8/8 Human Match Fit**
- S/P/M: {'Partial': 16, 'Strong': 15, 'Missing': 1}  ·  HMF: {3: 2, 5: 1, 4: 4, 2: 1}
- taxonomy: `v2real_df9143338be0` confirmed **matchable**
- Importance: lightweight / not exhaustively human-verified  ·  single annotator

## V2-Synthetic

- **21 human-reviewed** representative probe rows (9 round-1 + 12 representative-12); accepted 19 · edited 2
- scenario-category coverage: {'strong_partial_boundary': 3, 'partial_missing_boundary': 3, 'compound': 5, 'technology_adjacency': 3, 'project_vs_formal_work': 2, 'or_alternative': 2, 'role_core_mismatch': 3}  (all 7 ≥ 2)
- **44 probes scenario-derived only** — NOT represented as human-verified
- B01 kept as eligibility `PotentialGap`

## Validation

**All deterministic checks pass: True**

- v2_real_8_jobs: True
- v2_real_32_requirements: True
- v2_real_no_blank_human_match_label: True
- v2_real_8_hmf_ratings: True
- v2_real_hmf_in_1_5: True
- v2_real_every_scored_row_matchable: True
- v2_real_every_row_has_notes_and_evidence: True
- v2_real_no_synthetic_contamination: True
- synthetic_21_reviewed_rows: True
- synthetic_all_7_categories: True
- synthetic_no_pending_among_21: True
- synthetic_probe_accounting_65_21_44: True
- synthetic_frozen_view_reviewed_rows_match: True
- synthetic_frozen_view_full_gt_retained: True
- synthetic_b01_eligibility_potentialgap_not_forced: True
- all_pass: True

## Limitations

**V2-Real:** small N = 8 jobs; 32 core requirements only; requirement selection is representative, not exhaustive; companies often unknown (source metadata not supplied); Importance only lightly calibrated; single human annotator; not a production/publication benchmark.

**V2-Synthetic:** 50 synthetic jobs; 65 probes total; 21 representative probes human-reviewed; remaining 44 probes scenario-derived only; results are behavioral stress-test evidence; not real-world performance estimates.
