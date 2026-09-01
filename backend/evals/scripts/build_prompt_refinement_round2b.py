"""Build Prompt Refinement Round 2B artifacts.

Prompt C = job-fit-v3-rubric-refined-v2 = the frozen control instruction block + ONE inserted
block of exactly THREE compact rule groups (Technology Adjacency, Project vs Formal Work,
Strong/Partial/Missing Calibration). NO OR-list rule, NO compound rule, NO examples, NO new logic.
Production requirement_matcher.py is NOT modified.

Writes under backend/evals/prompt_refinement_round2b/:
  prompt_refinement_prompt_control.md
  prompt_refinement_prompt_b.md          (the rejected Round 2A full Prompt B, for reference)
  prompt_refinement_prompt_c.md
  prompt_refinement_prompt_diff.md
  prompt_refinement_prompt_hashes.json
  prompt_refinement_treatment_instructions.txt   (Prompt C instruction block, runner input)
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

OUT = BACKEND / "evals/prompt_refinement_round2b"
OUT.mkdir(parents=True, exist_ok=True)
R2A = BACKEND / "evals/prompt_ablation_round2a"
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
PROD_INSTRUCTIONS = full[:idx]

# --- Prompt C: exactly three compact rule groups. No OR-list. No compound. ---
REFINED_RULES = """
ADJUDICATION RULES (rubric-refined v2 — three calibration clarifications only; no new taxonomy,
scoring, eligibility, knowledge, OR-list, compound-decomposition, company, title, or preference
logic; no examples):

A. TECHNOLOGY ADJACENCY
- Related or adjacent technology is not automatically Partial. A Partial match requires evidence
  that meaningfully overlaps with the actual capability being requested.
- General AI / LLM / RAG experience alone should not automatically count as experience with a
  distinct specialised capability such as multimodal systems, speech / ASR, reinforcement-learning
  training, fine-tuning, model-training infrastructure, or specialised recommendation / search
  mechanisms.
- If the evidence is only general or neighbouring and does not demonstrate the requested
  capability, classify Missing.

B. PROJECT EXPERIENCE VS FORMAL WORK EXPERIENCE
- Project experience is valid matchable evidence. A direct and complete project may support Strong
  when the requirement asks for related practical experience, implementation, delivery,
  productisation, or hands-on application.
- When the requirement explicitly asks for formal professional-role experience, years in a job
  function, seniority, industry tenure, or professional ownership scope, project experience alone
  should not be treated as equivalent formal work experience. Relevant project evidence may support
  Partial in those cases.

C. STRONG / PARTIAL / MISSING CALIBRATION
- Strong: direct and sufficiently complete evidence at the level actually requested.
- Partial: meaningful but materially incomplete evidence.
- Missing: no meaningful evidence for the requested capability, or only general / adjacent evidence
  that does not demonstrate it.
- Do not use Partial merely because the model is uncertain.
"""

for anchor in ("\nIMPORTANCE:\n", "\nOUTPUT:\n"):
    if anchor in PROD_INSTRUCTIONS:
        INSERT_ANCHOR = anchor
        break
else:
    raise SystemExit("no insertion anchor")

pre, _, post = PROD_INSTRUCTIONS.partition(INSERT_ANCHOR)
PROMPT_C = pre + "\n" + REFINED_RULES.strip("\n") + "\n" + INSERT_ANCHOR + post

sha_a = hashlib.sha256(PROD_INSTRUCTIONS.encode()).hexdigest()
sha_c = hashlib.sha256(PROMPT_C.encode()).hexdigest()
prompt_b_txt = (R2A / "prompt_ablation_treatment_instructions.txt").read_text()
sha_b = hashlib.sha256(prompt_b_txt.encode()).hexdigest()

(OUT / "prompt_refinement_treatment_instructions.txt").write_text(PROMPT_C)
(OUT / "prompt_refinement_prompt_control.md").write_text(
    "# PROMPT_A / CONTROL — `job-fit-v3-matchable-only` instruction block (verbatim from production)\n\n"
    "Production `backend/app/services/requirement_matcher.py` is NOT modified.\n\n"
    "```\n" + PROD_INSTRUCTIONS.strip("\n") + "\n```\n")
(OUT / "prompt_refinement_prompt_b.md").write_text(
    "# PROMPT_B / REJECTED — `job-fit-v3-rubric-aligned-v1` (Round 2A full rubric)\n\n"
    "Reference only. **Rejected** in Round 2A: no model reached +0.05 Macro F1; compound rule\n"
    "regressed all three models; OR-list rule materially harmed kimi-k3; kimi-k3 suffered a 1-job\n"
    "coverage failure. Prompt C removes the OR-list and compound rules.\n\n"
    "```\n" + prompt_b_txt.strip("\n") + "\n```\n")
(OUT / "prompt_refinement_prompt_c.md").write_text(
    "# PROMPT_C / `job-fit-v3-rubric-refined-v2` (eval-only)\n\n"
    "Identical to PROMPT_A / CONTROL except for ONE inserted block of **three** compact rule groups\n"
    "(A Technology Adjacency, B Project vs Formal Work, C Strong/Partial/Missing Calibration),\n"
    "placed immediately before `IMPORTANCE:`. **No OR-list rule. No compound rule. No examples. No\n"
    "new scoring / eligibility / knowledge / company / title / preference logic.** Production prompt\n"
    "file NOT modified; used only by the eval runner.\n\n"
    "```\n" + PROMPT_C.strip("\n") + "\n```\n")

base_ok = (PROMPT_C.replace("\n" + REFINED_RULES.strip("\n") + "\n", "", 1) == PROD_INSTRUCTIONS)
(OUT / "prompt_refinement_prompt_hashes.json").write_text(json.dumps({
    "prompt_control_id": "job-fit-v3-matchable-only",
    "prompt_b_id": "job-fit-v3-rubric-aligned-v1 (REJECTED, Round 2A)",
    "prompt_c_id": "job-fit-v3-rubric-refined-v2",
    "control_instruction_block_sha256": sha_a,
    "prompt_b_instruction_block_sha256": sha_b,
    "prompt_c_instruction_block_sha256": sha_c,
    "production_requirement_matcher_sha256": hashlib.sha256((BACKEND / "app/services/requirement_matcher.py").read_bytes()).hexdigest(),
    "prompt_c_added_char_count": len(PROMPT_C) - len(PROD_INSTRUCTIONS),
    "prompt_b_added_char_count": len(prompt_b_txt) - len(PROD_INSTRUCTIONS),
    "prompt_c_base_byte_identical_outside_insert": base_ok,
    "insertion_anchor": INSERT_ANCHOR.strip(),
    "rules_in_c": ["A Technology Adjacency", "B Project vs Formal Work", "C Strong/Partial/Missing Calibration"],
    "rules_removed_vs_b": ["OR / alternative-list semantics", "Compound requirement / narrowest unmet subclaim"],
}, ensure_ascii=False, indent=1))

(OUT / "prompt_refinement_prompt_diff.md").write_text(
    "# Prompt Refinement Round 2B — Prompt Diff (A vs B vs C)\n\n"
    "| | id | added chars vs control | sha256 (instruction block) |\n|---|---|---|---|\n"
    f"| PROMPT_A / control | `job-fit-v3-matchable-only` | 0 | `{sha_a}` |\n"
    f"| PROMPT_B / rejected | `job-fit-v3-rubric-aligned-v1` | {len(prompt_b_txt) - len(PROD_INSTRUCTIONS)} | `{sha_b}` |\n"
    f"| PROMPT_C / refined | `job-fit-v3-rubric-refined-v2` | {len(PROMPT_C) - len(PROD_INSTRUCTIONS)} | `{sha_c}` |\n"
    f"| production `requirement_matcher.py` | (unchanged) | — | `{hashlib.sha256((BACKEND / 'app/services/requirement_matcher.py').read_bytes()).hexdigest()}` |\n\n"
    f"Prompt C base byte-identical to control outside the single insert: **{base_ok}**\n\n"
    "## UNCHANGED in C (vs control)\n"
    "- All `job-fit-v3-matchable-only` semantic instructions, Section D output contract, evidence\n"
    "  rules, output schema, requirement taxonomy, label set, and the JOB REQUIREMENTS / EVIDENCE\n"
    "  payloads. Transport, reasoning mode, temperature, max_tokens, normalization, MatchScoreService,\n"
    "  join key, metrics.\n\n"
    "## KEPT from Prompt B (3 of 5 rule groups, compacted)\n"
    "- **A. Technology Adjacency** — adjacent tech is not automatic Partial; general AI/LLM/RAG is\n"
    "  not automatic credit for multimodal / ASR / RL-training / fine-tuning / training-infra /\n"
    "  specialised rec-search; general-or-neighbouring-only → Missing.\n"
    "- **B. Project vs Formal Work** — complete project can support Strong for practical /\n"
    "  implementation / delivery / productisation / hands-on requirements; when formal\n"
    "  professional-role experience / job-function years / seniority / tenure / ownership scope is\n"
    "  explicitly requested, project alone is not equivalent — Partial at most.\n"
    "- **C. Label Calibration** — Strong = direct sufficiently-complete at the requested level;\n"
    "  Partial = meaningful but materially incomplete; Missing = no meaningful or only\n"
    "  general/adjacent evidence; Partial not for uncertainty.\n\n"
    "## REMOVED from Prompt B\n"
    "- **OR / alternative-list rule** — Round 2A: Sonnet improved substantially, qwen3.8-max only\n"
    "  modestly, **kimi-k3 materially regressed on the OR-list slice**. Finalists are kimi-k3 and\n"
    "  qwen3.8-max; Prompt C is not optimised for Sonnet. REMOVED.\n"
    "- **Compound requirement / narrowest-unmet-subclaim rule** — Round 2A: the compound slice\n"
    "  **regressed for all three tested models**. Rejected in its current wording. REMOVED.\n\n"
    "## NO new rules, NO examples, NO few-shot, NO Dataset V1 cases, NO Ground Truth. Prompt C is a\n"
    "REDUCTION of Prompt B, not another expansion.\n")

print(json.dumps({
    "prompt_c_sha256": sha_c, "control_sha256": sha_a, "prompt_b_sha256": sha_b,
    "prompt_c_added_chars": len(PROMPT_C) - len(PROD_INSTRUCTIONS),
    "prompt_b_added_chars": len(prompt_b_txt) - len(PROD_INSTRUCTIONS),
    "base_byte_identical_outside_insert": base_ok,
    "rules_in_c": ["A Technology Adjacency", "B Project vs Formal Work", "C Calibration"],
    "removed_vs_b": ["OR-list", "compound"],
}, ensure_ascii=False, indent=1))
