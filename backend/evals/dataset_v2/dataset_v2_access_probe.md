# Dataset V2 — Source Access Probe (this session)

Bounded, read-only probe of official career sources from the evaluation environment on
2026-09-01. No login, no CAPTCHA interaction, no private cookies, no undocumented endpoints,
no rate-limit or access-control circumvention. Purpose: record empirically which sources are
reachable for held-out collection (task §9: "If a source blocks access: record the
limitation and use another source").

| source | URL tried | result | usable for JD capture here? |
|---|---|---|---|
| ByteDance | `jobs.bytedance.com/en/position?...&location=CT_11` | 302 → `joinbytedance.com` global marketing landing page; China board not served as static content; "Careers in China" is a separate JS SPA | **No** (not without SPA navigation / region handling) |
| Alibaba | `talent.alibaba.com/off-campus/position-list` | redirected to `talent.alibaba.com` root — a BU hub page ("进入招聘官网" per business unit); each BU board is its own SPA, job detail often login-gated | **No** (not without per-BU SPA navigation) |
| Xiaohongshu | `job.xiaohongshu.com/recruitment/social` | HTTP 404 | **No** (path not valid; correct entry not confirmed this session) |
| Tencent | `careers.tencent.com/en-us/search.html?keyword=product manager` | 200 — listings and full JD body render and are readable (same source class used for Dataset V1) | **Yes** |

## Implications

- The sources that reliably render full JD text here are the same官方 career sites used for
  Dataset V1 (Tencent Careers; by prior art Baidu Careers, Huawei Careers). Building V2
  only from those **reproduces the V1 Tencent/Baidu concentration bias**, which §4/§5
  explicitly require correcting.
- Broad company diversity (ByteDance, Alibaba, Meituan, JD, Xiaomi, Kuaishou, Didi, Ant,
  Trip.com, financial institutions, AI startups, enterprise-SaaS) sits behind
  JavaScript-rendered career SPAs, per-BU sub-sites, or login walls that this environment
  cannot traverse without interactive navigation — and, per §9, never via any bypass.
- No JD text was collected, paraphrased, translated, or reconstructed. Fabricated or
  memory-reconstructed JDs would void the held-out property of Dataset V2 and are
  prohibited by the task.

## Consequence

Dataset V2 job collection is a **human-in-the-loop step** (or an explicitly authorised
interactive collection session). This session prepared every downstream artifact
(schema, quotas, skeleton files, V1 exclusion set, dedup/balance frameworks, frozen
annotation template and adjudication guide, manifest) so collection can proceed directly
into the skeleton without further scaffolding.
