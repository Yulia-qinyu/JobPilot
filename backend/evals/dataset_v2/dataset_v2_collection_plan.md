# Dataset V2 — Collection Plan (Sampling Frame)

**Status:** specification only. No jobs collected yet. This file defines the quotas a
human collector fills; it contains **no job data and no model output**.

Dataset V2 is a **held-out validation/test set**. It must be collected and adjudicated
**without running either finalist model** (`qwen3.8-max + job-fit-v3-rubric-refined-v2`,
`kimi-k3 + job-fit-v3-matchable-only`) and without looking at any model prediction.

## 1. Size

| | value |
|---|---|
| minimum before freeze | 50 jobs |
| preferred target | 60 jobs |
| hard cap this phase | 70 jobs |

## 2. Geography (Mainland China only)

Preferred cities: 北京, 上海, 深圳, 广州, 杭州. Other Mainland cities allowed when useful.
No single city should dominate — keep every city ≤ ~40% and aim for ≥ 4 cities with
meaningful counts. (V1 was 北京 53% / 深圳 33%.)

## 3. Language

≥ 80% Chinese JD (`language = zh`). A small English-JD control subset is allowed.
**Do not translate JDs.** Preserve the employer's original wording. Language is classified
`zh` when substantive CJK chars ≥ Latin alphabetic chars in the responsibilities+requirements.

## 4. Company diversity (major V1 correction)

| | value |
|---|---|
| distinct companies — minimum | 12 |
| distinct companies — preferred | 15–20 |
| single-company share — preferred cap | 15% |
| single-company share — absolute cap | 20% |
| Tencent + Baidu combined | must **not** dominate (V1 was 87%) |

**Candidate sources (examples only — do not force inclusion):** ByteDance, Alibaba,
Ant Group, Tencent, Baidu, Meituan, JD, Xiaomi, Huawei, Kuaishou, Didi, Xiaohongshu,
Trip.com, Lenovo, Microsoft China, Amazon China, financial institutions, FinTech firms,
AI startups, enterprise-SaaS firms.

Suggested per-company cap for a 60-job set: **≤ 9 jobs** (15%). Prefer 3–5 each across
15–18 companies.

## 5. Career-stage balance (major V1 correction)

Record `career_stage` for every job. Allowed normalized values:
`campus_new_grad`, `early_career`, `experienced`, `unknown`.

| stage | target share | ~count @ 60 |
|---|---|---|
| campus_new_grad | 20–30% | 12–18 |
| early_career (~0–3 yrs) | 30–40% | 18–24 |
| experienced | 30–45% | 18–27 |

Do **not** infer a hard years requirement the JD does not state. Use `unknown` when the
JD gives no stage/seniority signal.

## 6. Role-family coverage

| role_family | target share | ~count @ 60 |
|---|---|---|
| ai_product | 35–45% | 21–27 |
| general_product | 15–20% | 9–12 |
| data_product | 10–15% | 6–9 |
| platform_enterprise_product | 10–15% | 6–9 |
| strategy_growth_fintech_product | 10–15% | 6–9 |
| mismatched_control (negative) | 5–10% | 3–6 |

Percentages are guidance, not exact arithmetic — prioritise useful evaluation diversity.

## 7. AI-subdomain diversity (technology-adjacency was a known V1 error slice)

Within `ai_product` (and mismatched AI controls), spread across **≥ 8 distinct** subdomains.
Record `ai_subdomain` per job. Menu:

`llm_applications`, `agent`, `rag_knowledge_systems`, `ai_platform`, `ai_tools`,
`multimodal`, `speech_asr`, `recommendation_search`, `ai_infrastructure`, `enterprise_ai`,
`ai_productivity`, `ai_consumer_products`, `ai_commercialisation`.

Avoid making every AI role a generic "LLM PM".

## 8. Source policy (§9)

**Prefer:** official company career pages, company-controlled recruiting pages, public
official job listings.
**Allowed:** public recruiting pages where access is lawful and needs no bypass.
**Never:** bypass CAPTCHA; use stolen/private cookies; use undocumented private endpoints
obtained by circumvention; circumvent rate limits or access controls; automate login bypass.

If a source blocks access → record the limitation in `access_note` and use another source.
Record `source_type` ∈ `official_company_career_page | company_controlled_recruiting_page | public_official_listing`.

## 9. Exclusions

Every candidate is checked against `dataset_v2_v1_overlap_report.json` (all 30 V1 jobs) on:
exact `job_id`, canonical URL, normalized `title|company|city`, and JD-text similarity
(4-gram Jaccard ≥ 0.72 or SequenceMatcher ≥ 0.86). Any hit → reject the candidate.
Within-V2 duplicates are checked the same way (`dataset_v2_dedup_report.json`).

## 10. Per-job capture checklist

For each accepted job, fill every `job_record_fields` key in `dataset_v2_schema.json`:
verbatim `job_description_raw` (+ split sections when separable), `job_url`, `source`,
`source_job_id`, `source_type`, `company`, `title`, `location`, `career_stage`,
`role_family`, `ai_subdomain`, `language`, `collected_at`, `collector`, `access_note`.
Leave `education_requirement` / `experience_requirement` / `graduation_year_requirement` /
`salary_text` blank unless the JD states them explicitly. All `human_*` fields stay blank.
