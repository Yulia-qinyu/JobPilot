# Cross-Provider Prompt Parity — `job-fit-v3-matchable-only`

Provider-neutral decomposition of the **current production** semantic matcher prompt.
Source of truth: `backend/app/services/requirement_matcher.py` SHA-256
`e99ed02728452d6f50b39867a6dbf5e5a79e0fb9d78b610d66297f5d6a1ad19b`. **No wording or meaning is
changed here.** Every provider adapter must send parts A + B + C and require output contract D with
identical semantics.

---

## A. Canonical semantic instructions (byte-identical for every provider)

> You are JobPilot's evidence-grounded requirement matcher. Match every supplied
> job requirement against only the supplied candidate evidence catalog. Return exactly one
> requirement_match for every requirement_id, with no duplicates and no unknown IDs.
>
> MATCH RULES:
> - Strong: direct, convincing evidence satisfies the requirement.
> - Partial: related evidence exists but scope, depth, duration, or exact capability is incomplete.
> - Missing: no eligible evidence supports the requirement. Missing must use an empty evidence list.
> - Strong and Partial must cite one or more exact evidence_source_ids from the catalog.
> - Cite at most the four strongest, most direct evidence sources for each requirement.
> - Never invent candidate facts, achievements, dates, employers, credentials, or evidence IDs.
> - A resume skill keyword alone is normally Partial unless other factual evidence demonstrates use.
> - Evidence IDs beginning with manual_confirmed:profile: are user-confirmed Candidate Profile facts.
> - A confirmed graduation cohort supports only that cohort/campus identity; it does not prove a degree.
> - For a compound requirement such as "2027届本科及以上学历", use Strong only when separate
>   eligible evidence supports both the graduation cohort and the required degree. Use Partial when
>   only one component is supported. Never infer a degree from graduation cohort metadata.
>
> IMPORTANCE:
> - Critical: central explicit requirement or essential responsibility.
> - Important: meaningful requirement that is not a strict gate.
> - Preferred: only an explicit preferred, plus, nice-to-have, 优先, or 加分 requirement. Words
>   such as 熟悉/familiar describe proficiency and do not alone make a requirement Preferred.
>
> HARD REQUIREMENTS — BE CONSERVATIVE:
> - Mark hard only when the requirement itself contains explicit mandatory or eligibility language,
>   such as must, required, mandatory, at least X years, a required certification/degree/license,
>   legal work eligibility, an explicit graduating cohort/date, 必须, 至少, 不少于, 工作许可,
>   明确毕业届别, or mandatory qualification language.
> - Never mark preferred, familiar with, plus, nice to have, 优先, 熟悉, or 加分 as hard.
> - A hard requirement must use importance Critical.
> - hard_requirement_category must be eligibility, experience, qualification, other, or none.
> - Use none whenever is_hard_requirement is false.
> - Requirements with source_kind=v2_matchable have already passed the V2 taxonomy boundary. They
>   are evidence-matchable capabilities, never eligibility gates; return is_hard_requirement=false
>   and hard_requirement_category=none for them.
>
> OUTPUT:
> - Write summary, reasons, preparation titles, and actions in natural Simplified Chinese.
> - Keep each reason focused and concise, normally no more than two sentences.
> - Preserve company, project, and technology names such as AI, LLM, Agent, RAG, SQL, and Python.
> - suggested_preparation must be concise, prioritized, linked to valid requirement IDs, and must not
>   rewrite the resume or tell the user to claim unsupported experience.

**Nothing may be added to Section A per candidate** — no OR-list rule, no adjacency guardrail, no
project-vs-work adjudication, no narrowest-unmet-subclaim guidance, no failure cases, no human notes.

## B. Dynamic job / requirement payload (per job, identical construction across providers)

`JOB REQUIREMENTS:` followed by a JSON array, one object per frozen matchable requirement of the job:

```
{
  "requirement_id":  "<frozen reqv2_* id>",
  "requirement_text":"<normalized_requirement>",
  "context":         "<source_text>",
  "importance_hint": "high|medium|low",       // Critical->high, Important->medium, Preferred->low
  "source_kind":     "v2_matchable"
}
```

Serialised with `json.dumps(..., ensure_ascii=False)` exactly as production does.

## C. Frozen evidence payload (identical for every job and every provider)

`ELIGIBLE CANDIDATE EVIDENCE:` followed by a JSON array, one object per item of the frozen 30-item
`candidate_evidence_snapshot`:

```
{
  "evidence_source_id":"<source_type>:<source_id>",   // == the frozen catalog id
  "source_type":       "resume_extracted|manual_confirmed",
  "text":              "<text_summary>",
  "context":           "<context>"
}
```

`resume_hash a5c64e177db9454e4562c82bfd3e2dd82aeca613b6b3ba50c5618e66c71e4f4f`. No human adjudication
facts (GoFin C-end / AI-platform / Chinese-native) are in this payload.

## D. Expected output contract (equivalent semantics on every provider)

```
{
  "summary": "<string, Simplified Chinese>",
  "requirement_matches": [
    {
      "requirement_id": "<echo of a submitted id; exactly one per id; no dupes; no unknown ids>",
      "match_label":    "Strong | Partial | Missing",     // maps to production match_status
      "evidence_ids":   ["<frozen catalog id>", ...],     // empty for Missing; >=1 for Strong/Partial
      "reason":         "<string, Simplified Chinese, <= ~2 sentences>"
    }
  ],
  "suggested_preparation": [
    { "title": "<string>", "action": "<string>", "priority": "High|Medium|Low", "requirement_ids": ["<id>", ...] }
  ]
}
```

The production wire schema (`FitAnalysisOutput` / `RequirementMatchOutput`) also carries
`importance`, `is_hard_requirement`, `hard_requirement_category`, `confidence`. Adapters must request
those fields too (Section A already instructs the model on them) so the output can be fed to the
**unchanged** production `_normalize_matches` without any adapter-side semantic fill-in.

## Per-provider transport placement (TRANSPORT_SERIALIZATION_ONLY — no semantic change)

| provider | placement of A / B / C | schema binding of D | temperature |
|---|---|---|---|
| **Anthropic** (reference) | single user message: A + "\n\nJOB REQUIREMENTS:\n" + B + "\n\nELIGIBLE CANDIDATE EVIDENCE:\n" + C (production layout) | `messages.parse(output_format=FitAnalysisOutput)` | `temperature=0` |
| **Gemini** | either one user `content` = A+B+C, **or** system_instruction = A / user = B+C (transport split, no meaning change) | `generateContent` with `responseMimeType="application/json"` + `responseSchema` = JSON Schema of `FitAnalysisOutput`; OR OpenAI-compat `/v1beta/openai/` `response_format={"type":"json_schema", ...}` | `temperature=0` if accepted; else omit and record |
| **Qwen (DashScope)** | OpenAI-compat: system = A / user = B+C, or single user A+B+C | `response_format={"type":"json_schema","json_schema":{...}}` if supported; else `{"type":"json_object"}` + record `structured_output_limitation` | `temperature=0` if accepted; else omit and record |
| **DeepSeek** | OpenAI-compat: system = A / user = B+C | `response_format={"type":"json_object"}`; if the API requires the literal token `json` in the prompt, append a transport-only line **"Respond only with a single JSON object."** — apply the identical line to **every** provider for parity, and label it `transport_only` | `temperature=0` if accepted; else omit and record |

Any provider-specific system/user split, JSON-mandate line, or omitted `temperature` is logged in the
adapter's `transport_metadata` and classified `TRANSPORT_SERIALIZATION_ONLY`. The model-facing
**semantic task** — Sections A + B + C + D — is equivalent for all candidates.
