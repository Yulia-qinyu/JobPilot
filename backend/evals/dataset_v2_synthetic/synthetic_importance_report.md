# Synthetic Challenge Set — Importance Review (schema upgrade)

- Focused probe requirements: **65** — every one now has an importance-review slot.
- Schema fields added (in `synthetic_importance_focused_review.csv`, raw artifacts untouched): `draft_importance`, `importance_rationale`, `human_importance`, `importance_review_status`, `human_importance_notes`.
- Allowed `human_importance`: Critical / Important / Preferred.

## Draft importance distribution over the 65 probes

| importance | count |
|---|---|
| Critical | 52 |
| Important | 13 |

## By requirement type

- matchable: {'Critical': 46, 'Important': 13}
- eligibility: {'Critical': 6}

All 65 require an explicit human importance decision (none were importance-reviewed at generation — the generator assigned importance mechanically by scenario role).
Eligibility probes get a decision too, but eligibility never enters Match Score.
