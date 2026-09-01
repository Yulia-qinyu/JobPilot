"""Build the Round 2A Prompt / Rubric Communication Ablation prompt artifacts.

Captures the EXACT production instruction block from the unchanged production RequirementMatcher
(no edit to backend/app/**), writes:
  prompt_ablation_prompt_control.md    — the production instruction block, verbatim
  prompt_ablation_prompt_treatment.md  — production block + the 5 frozen adjudication rules, inserted
  prompt_ablation_prompt_diff.md       — auditable UNCHANGED / ADDED-ONLY diff
  prompt_ablation_prompt_hashes.json   — sha256 of both instruction blocks

The treatment file contains ONLY the instruction block (everything the production prompt places
before the "JOB REQUIREMENTS:" payload). The runner appends the byte-identical JOB REQUIREMENTS +
ELIGIBLE CANDIDATE EVIDENCE payloads + Section D, so PROMPT_A and PROMPT_B differ by exactly the
inserted rule block.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path("/Users/yulia/Documents/JobPilot/backend")
sys.path.insert(0, str(BACKEND))

from app.schemas.fit_analysis import EvidenceSourceRead                # noqa: E402
from app.services.evidence_catalog import EvidenceCatalog             # noqa: E402
from app.services.requirement_catalog import RequirementCatalog, ScoredRequirement  # noqa: E402
from app.services.requirement_matcher import RequirementMatcher       # noqa: E402

OUT = BACKEND / "evals/prompt_ablation_round2a"
OUT.mkdir(parents=True, exist_ok=True)
REQ_MARKER = "\n\nJOB REQUIREMENTS:\n"


class _Captured(Exception):
    pass


class _Cap:
    def __init__(self):
        self.captured = None
        self.model = "capture"
        self.last_call_metrics = {}

    def generate(self, *, prompt, output_model, tool_name):
        self.captured = prompt
        raise _Captured()


# minimal synthetic catalog/evidence just to trigger prompt assembly (never sent anywhere)
cat = RequirementCatalog(
    requirements=[ScoredRequirement(requirement_id="x", text="x", context="x",
                                    importance_hint="medium", source_kind="v2_matchable")],
    structured_jd_hash="build-only")
ev = EvidenceCatalog(sources=[EvidenceSourceRead(source_type="resume_extracted", source_id="x",
                                                 text="x", context="x")],
                     resume_hash="x", experience_bank_hash="x")
cap = _Cap()
try:
    RequirementMatcher(cap).analyze(cat, ev)
except _Captured:
    pass
full = cap.captured
idx = full.index(REQ_MARKER)
PROD_INSTRUCTIONS = full[:idx]   # the production instruction block, verbatim

# ------------------------------------------------------------------ the 5 frozen adjudication rules
ADJUDICATION_RULES = """
ADJUDICATION RULES (rubric-aligned v1 — clarify existing Strong/Partial/Missing boundaries only;
they add no new taxonomy, scoring, eligibility, knowledge, company, title, or preference logic):

1. OR / ALTERNATIVE-LIST SEMANTICS
- When a requirement explicitly lists alternatives ("A or B", "A / B", "one of A, B, C",
  "experience in X, Y, or Z"), treat the listed branches as alternatives unless the wording clearly
  requires all of them.
- If the candidate strongly satisfies one explicitly allowed branch, do not reduce the match merely
  because the other alternative branches are not covered.
- Independent qualifiers still apply and are evaluated separately: years of experience, proficiency
  level, ownership scope, formal work experience, seniority, and domain depth.

2. TECHNOLOGY-ADJACENCY GUARDRAIL
- Related or adjacent technologies are not automatically evidence for Partial.
- General LLM / RAG / AI experience must not automatically be credited as experience in a more
  specific technical area such as multimodal systems, ASR / speech, reinforcement-learning training,
  fine-tuning, model-training infrastructure, or specialised recommendation / search mechanisms.
- A Partial match requires evidence that meaningfully overlaps with the actual capability requested.
  General familiarity or a neighbouring technology alone may still be Missing.

3. PROJECT EXPERIENCE VS FORMAL WORK EXPERIENCE
- Project experience is valid matchable evidence.
- If a requirement asks for related-direction experience, productisation, implementation, delivery,
  practical application, or hands-on project experience, a direct and complete project may support
  Strong.
- If a requirement explicitly asks for formal professional-role experience, years in a specific job
  function, seniority, industry tenure, or full ownership in a professional setting, project
  experience alone usually cannot support Strong. It may support Partial if it demonstrates relevant
  capability, but it is not equivalent to the requested formal work experience.

4. COMPOUND REQUIREMENT / NARROWEST UNMET SUBCLAIM
- When a single requirement contains multiple subclaims that are jointly required, do not assign
  Strong merely because one subclaim is supported. Judge the requirement against its
  least-supported material subclaim.
- If the requirement asks for capability A AND capability B, Strong requires strong support for
  both. If one material subclaim is only partially supported, the requirement is usually Partial.
  If a material subclaim is entirely unsupported, the requirement may be Missing depending on that
  subclaim's importance.
- Do not split the requirement into new rows; judge the existing canonical requirement as written.

5. EXPLICIT STRONG / PARTIAL / MISSING CALIBRATION
- Strong: the candidate has direct, sufficiently complete evidence for the requirement at the level
  actually requested.
- Partial: the candidate has meaningful but incomplete evidence — for example only part of a
  compound requirement, weaker depth / proficiency than requested, relevant project evidence where
  formal work experience is explicitly required, or adjacent but materially overlapping experience.
- Missing: the candidate lacks evidence for the requested capability, or has only general / adjacent
  evidence that does not meaningfully demonstrate the requested requirement.
- Partial must not be used as a generic uncertainty bucket.
"""

# Insert the rule block right before the existing "IMPORTANCE:" section (keeps all match-calibration
# guidance together, immediately after the MATCH RULES block). If that anchor is ever absent, fall
# back to inserting before "OUTPUT:".
for anchor in ("\nIMPORTANCE:\n", "\nOUTPUT:\n"):
    if anchor in PROD_INSTRUCTIONS:
        INSERT_ANCHOR = anchor
        break
else:
    raise SystemExit("could not find an insertion anchor in the production instruction block")

pre, _, post = PROD_INSTRUCTIONS.partition(INSERT_ANCHOR)
TREATMENT_INSTRUCTIONS = pre + "\n" + ADJUDICATION_RULES.strip("\n") + "\n" + INSERT_ANCHOR + post

# ------------------------------------------------------------------ write artifacts
(OUT / "prompt_ablation_prompt_control.md").write_text(
    "# PROMPT_A_CONTROL — instruction block (verbatim from production RequirementMatcher)\n\n"
    "prompt_control_id: `job-fit-v3-matchable-only`\n\n"
    "This is the exact instruction text the production prompt places before the "
    "`JOB REQUIREMENTS:` payload. It is reproduced here for audit; the production file "
    "`backend/app/services/requirement_matcher.py` is NOT modified.\n\n"
    "```\n" + PROD_INSTRUCTIONS.strip("\n") + "\n```\n")

(OUT / "prompt_ablation_prompt_treatment.md").write_text(
    "# PROMPT_B_RUBRIC_ALIGNED_V1 — instruction block (eval-only treatment)\n\n"
    "prompt_treatment_id: `job-fit-v3-rubric-aligned-v1`\n\n"
    "Identical to PROMPT_A_CONTROL except for the inserted **ADJUDICATION RULES (rubric-aligned v1)** "
    "block (5 frozen adjudication rules), placed immediately before the existing `IMPORTANCE:` "
    "section. No Ground-Truth examples, no benchmark cases, no model-specific hints, no new "
    "taxonomy / scoring / eligibility / knowledge / preference logic. The production prompt file is "
    "NOT modified; this text is used only by the eval runner.\n\n"
    "```\n" + TREATMENT_INSTRUCTIONS.strip("\n") + "\n```\n")

# raw instruction-only file the runner consumes
(OUT / "prompt_ablation_treatment_instructions.txt").write_text(TREATMENT_INSTRUCTIONS)

sha_a = hashlib.sha256(PROD_INSTRUCTIONS.encode()).hexdigest()
sha_b = hashlib.sha256(TREATMENT_INSTRUCTIONS.encode()).hexdigest()
(OUT / "prompt_ablation_prompt_hashes.json").write_text(json.dumps({
    "prompt_control_id": "job-fit-v3-matchable-only",
    "prompt_treatment_id": "job-fit-v3-rubric-aligned-v1",
    "control_instruction_block_sha256": sha_a,
    "treatment_instruction_block_sha256": sha_b,
    "production_requirement_matcher_sha256": hashlib.sha256((BACKEND / "app/services/requirement_matcher.py").read_bytes()).hexdigest(),
    "insertion_anchor": INSERT_ANCHOR.strip(),
    "added_char_count": len(TREATMENT_INSTRUCTIONS) - len(PROD_INSTRUCTIONS),
    "base_is_byte_identical_outside_insert": (TREATMENT_INSTRUCTIONS.replace("\n" + ADJUDICATION_RULES.strip("\n") + "\n", "", 1) == PROD_INSTRUCTIONS),
}, ensure_ascii=False, indent=1))

(OUT / "prompt_ablation_prompt_diff.md").write_text(
    "# Prompt Ablation Round 2A — Prompt Diff (audit)\n\n"
    "| | value |\n|---|---|\n"
    f"| prompt_control | `job-fit-v3-matchable-only` |\n"
    f"| prompt_treatment | `job-fit-v3-rubric-aligned-v1` (eval-only) |\n"
    f"| control instruction-block sha256 | `{sha_a}` |\n"
    f"| treatment instruction-block sha256 | `{sha_b}` |\n"
    f"| production `requirement_matcher.py` sha256 | `{hashlib.sha256((BACKEND / 'app/services/requirement_matcher.py').read_bytes()).hexdigest()}` (UNCHANGED) |\n"
    f"| added characters | {len(TREATMENT_INSTRUCTIONS) - len(PROD_INSTRUCTIONS)} |\n"
    f"| base byte-identical outside the single insert | "
    f"{TREATMENT_INSTRUCTIONS.replace(chr(10) + ADJUDICATION_RULES.strip(chr(10)) + chr(10), '', 1) == PROD_INSTRUCTIONS} |\n\n"
    "## UNCHANGED\n"
    "- All current `job-fit-v3-matchable-only` semantic instructions (matcher role, MATCH RULES,\n"
    "  IMPORTANCE, HARD REQUIREMENTS, OUTPUT), verbatim.\n"
    "- Section D output contract (`summary` / `requirement_matches[{requirement_id, match_label,\n"
    "  evidence_ids, reason}]` / `suggested_preparation`).\n"
    "- Evidence rules, output schema, requirement taxonomy, label set {Strong, Partial, Missing}.\n"
    "- The `JOB REQUIREMENTS:` and `ELIGIBLE CANDIDATE EVIDENCE:` payloads (byte-identical).\n"
    "- Transport, reasoning mode, temperature policy, max_tokens, normalization, MatchScoreService,\n"
    "  join key, metrics.\n\n"
    "## ADDED ONLY — one block: `ADJUDICATION RULES (rubric-aligned v1)`, before `IMPORTANCE:`\n"
    "1. OR / alternative-list semantics (branches are alternatives unless wording requires all;\n"
    "   independent qualifiers — years, proficiency, ownership scope, formal work experience,\n"
    "   seniority, domain depth — still apply).\n"
    "2. Technology-adjacency guardrail (adjacent tech is not automatic Partial; general LLM/RAG/AI\n"
    "   is not automatic credit for multimodal / ASR / RL-training / fine-tuning / training infra /\n"
    "   specialised rec-search; Partial needs materially overlapping evidence; else Missing).\n"
    "3. Project vs formal work experience (a complete project can support Strong for\n"
    "   direction/productisation/implementation/delivery requirements; project alone usually cannot\n"
    "   support Strong when formal professional-role experience / job-function years / seniority /\n"
    "   tenure / full professional ownership is explicitly requested — Partial at most).\n"
    "4. Compound requirement / narrowest unmet subclaim (judge against the least-supported material\n"
    "   subclaim; A AND B needs both strong for Strong; one partial subclaim -> Partial; an\n"
    "   unsupported material subclaim -> possibly Missing; do not split the row).\n"
    "5. Explicit Strong / Partial / Missing calibration (Strong = direct sufficiently-complete\n"
    "   evidence at the requested level; Partial = meaningful but incomplete; Missing = lacking or\n"
    "   only general/adjacent evidence; Partial must not be a generic uncertainty bucket).\n\n"
    "The added block contains NO Ground-Truth labels, NO Human Match Fit, NO Dataset V1 job/"
    "requirement ids, NO baseline wrong predictions, NO per-model failure examples, NO score deltas,"
    " NO benchmark rankings, NO company/title heuristics. The rules are generic re-statements of the"
    " frozen human adjudication rubric.\n")

print(json.dumps({
    "control_sha256": sha_a, "treatment_sha256": sha_b,
    "added_chars": len(TREATMENT_INSTRUCTIONS) - len(PROD_INSTRUCTIONS),
    "insertion_anchor": INSERT_ANCHOR.strip(),
    "base_byte_identical_outside_insert": (TREATMENT_INSTRUCTIONS.replace("\n" + ADJUDICATION_RULES.strip("\n") + "\n", "", 1) == PROD_INSTRUCTIONS),
    "files": sorted(p.name for p in OUT.glob("prompt_ablation_prompt_*")) + ["prompt_ablation_treatment_instructions.txt"],
}, ensure_ascii=False, indent=1))
