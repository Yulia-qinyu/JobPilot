# Dataset V2 — Batch 2 Balance Report (provisional)

**Status: NOT_READY.** 16 human-pasted real Chinese JDs staged (`dataset_v2_batch2_staging.json`).
Source URLs pending; **0 source-verified**, **0 verbatim-source-verified**, **0 in the frozen
corpus**. All figures provisional. **No model run. No synthetic data.**

**Caveat:** 13 / 16 Batch 2 jobs have `company = unknown` and 15 / 16 have `location = unknown`
(not stated in the pasted text; not inferred). Company-diversity and geographic conclusions
are therefore limited for Batch 2.

## View A — Batch 2 alone (16)

| dimension | value |
|---|---|
| candidate jobs | 16 |
| distinct **known** companies | 2 — 字节跳动 (×2: 小荷健康, 火山引擎), 水滴公司 (×1) |
| unknown-company jobs | 13 |
| city | 北京市 2 (#11, #16); unknown 14 |
| **career_stage** | campus_new_grad 7 · unknown 8 · experienced 1 · early_career 0 |
| **role_family** | ai_product 8 · platform_enterprise_product 5 · strategy_growth_fintech_product 1 · mismatched_control 1 · general_product 1 · data_product 0 |
| language | zh 16 (100%) |
| AI-subdomain coverage | llm_applications 9 · agent 5 · enterprise_ai 4 · rag_knowledge_systems 3 · ai_platform 3 · ai_consumer_products 3 · recommendation_search 2 · ai_productivity 1 · ai_tools 1 · multimodal 1 → **10 distinct** |
| duplicates | 0 exact, 0 probable near (within B2); 0 vs Batch 1; 0 vs V1 |
| source verification | pending 16 / verified 0 |
| requirement candidates (heuristic segmentation) | ~196 total (~12/job); production parser **not** run |

### Career-stage evidence notes
- campus_new_grad (7): #1 (校招 + 硕士), #2 (2027届在读), #8 (2027届), #11 (2027年应届生), #12 (27届培训生), #15 (2026-09–2027-08 毕业), #16 (2027届应届).
- unknown (8): #3, #4, #5, #6, #7, #9, #10→**experienced** (see below), #13, #14 — no explicit graduation cohort and no explicit professional-years requirement. #6 (管培生) implies new-grad hiring but states no cohort → conservative `unknown`. Internship-*preferred* never sets the stage.
- experienced (1): #10 — requires a prior AI-product track record ("有推荐系统、搜索算法、对话机器人等落地案例，熟悉技术边界与商业化逻辑" + 算法工程背景).
- **early_career: 0** — no job states an explicit 1–3-year professional requirement.

### Role-family rationale notes (classified by core responsibility, not by AI mentions)
- `strategy_growth_fintech_product` #4 — user-operations / conversion / channel growth on an insurance platform; AI used only as an ops tool.
- `mismatched_control` #6 — private-domain (私域) user-operations trainee (裂变/朋友圈 SOP/SCRM/RFM), not a PM role (matches the §8 example).
- `general_product` #15 — general PM; "关注AI在工作中的实际应用" only → stays general.
- `platform_enterprise_product` #3 (internal office/R&D efficiency), #5 (network-security product), #8 (火山引擎 enterprise AI platform, low-code/zero-code), #10 (HR-tech AI recruitment), #13 (agent platform / knowledge-mgmt platform + SaaS).
- `ai_product` #1, #2, #7, #9, #11, #12, #14, #16.
- `data_product` — **0**.

## View B — Batch 1 provisional (10) + Batch 2 provisional (16) = 26

| dimension | value |
|---|---|
| candidate jobs | 26 (0 accepted, 0 source-verified) |
| distinct **known** companies | 4 — 百度 5, 京东 5, 字节跳动 2, 水滴 1 |
| unknown-company jobs | 13 |
| big-tech concentration | 百度+京东 = **38.5%**; +字节跳动 = **46.2%** of the pool |
| city | 北京市 9 · 深圳市 2 · 上海市 1 · unknown 14 |
| **career_stage** | campus_new_grad 9 · experienced 7 · unknown 10 · **early_career 0** |
| **role_family** | ai_product 12 · platform_enterprise_product 8 · general_product 3 · data_product 1 · strategy_growth_fintech_product 1 · mismatched_control 1 |
| language | zh 26 (100%) |
| distinct AI-subdomains | 13 |
| duplicates | 0 exact, 0 probable near across the pool; 0 vs V1 |
| source verification | pending 26 / verified 0 |

## View C — V2-Real candidate pool after removing known V1 duplicates

26 provisional jobs. Batch 1's 3 exact V1 duplicates were already rejected; Batch 2 has 0 V1
duplicates. So the V2-Real candidate pool = **26 provisional / 0 source-verified / 0 frozen**.
Known companies: 百度, 京东, 字节跳动, 水滴. Unknown-company jobs: 13.

## Target-band comparison (new V2-Real target: 30 preferred / 24 minimum real Chinese JDs)

| target | status |
|---|---|
| 24–30 real Chinese JDs | **26 provisional** — count met, but **0 source-verified** |
| 100% Chinese-language | **PASS** (26/26 zh) |
| ≥ 10 distinct known companies | **FAIL** — 4 known; 13 unknown-company jobs |
| avoid Tencent/Baidu/JD concentration | **AT RISK** — 百度+京东 = 38.5% |
| campus_new_grad present | PASS (9) |
| early_career present | **FAIL — 0** |
| experienced present | PASS (7) |
| data_product | **THIN — 1** |
| strategy_growth_fintech_product | **THIN — 1** |
| platform_enterprise_product | PASS (8) |
| general_product | THIN — 3 |
| mismatched_control | THIN — 1 |
