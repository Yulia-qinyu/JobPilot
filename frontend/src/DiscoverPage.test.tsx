import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppNavigation } from "./App";
import DiscoverPage, { DiscoveryFiltersBar, DiscoveryProgress, DiscoveryResultCard, PersonalizationToggle, RefinementPanel } from "./DiscoverPage";
import { nextRefinementSelection } from "./discovery-selection";
import { buildDiscoveryParams } from "./discovery-utils";
import type { DiscoveryResult, DiscoverySession } from "./types";

const session: DiscoverySession = {
  id: "session-1", state: "Searching", source: "bytedance", discovered_count: 120,
  selected_sources: ["bytedance"],
  selected_source_plans: ["bytedance:experienced"],
  source_plan: { requested_companies: ["字节跳动"], selected_sources: [{ source_key: "bytedance", company_id: "bytedance", company_name: "字节跳动", provider: "bytedance", channel: "experienced", adapter_key: "bytedance", tenant: null }], unsupported_companies: [], coverage_status: "full", coverage_message: "已搜索字节跳动官方招聘源。" },
  source_progress: [{ source: "bytedance", provider: "bytedance", tenant: null, company: "字节跳动", channel: "experienced", status: "Searching", discovered_count: 120, duration_seconds: null, error_code: null }],
  refinement_groups: [],
  required_refinement_groups: [], optional_refinement_groups: [],
  processed_count: 80, result_count: 0, duplicate_count: 2, failed_count: 0,
  source_failures: [], error_code: null, result_cap_reached: false,
  claude_api_calls: 0, intent_input_tokens: null, intent_output_tokens: null, phase3_calls: 0, created_at: "2026-08-25T00:00:00Z",
  personalization_status: "Off", personalization_message: null, personalization_latency_ms: null, source_refetch_count: 0,
  expires_at: "2026-08-25T01:00:00Z", completed_at: null,
  search_context: {
    session_id: "session-1", input_kind: "bytedance_search_url", raw_input: "https://jobs.bytedance.com/experienced/position",
    explicit_constraints: { role_terms: ["AI Product"], role_families: ["ai_product"], locations: ["北京"], companies: ["字节跳动"], company_groups: [], job_functions: ["product_management"], industries: [], domains: ["ai_agent"], seniority: [], recruitment_types: ["社招"] },
    include_terms: [], exclusions: [], freeform_terms: [], explicit_concepts: [{ raw_text: "北京", normalized_id: "北京", dimension: "location", polarity: "include", source: "user_explicit" }], explicit_concept_tag_ids: [], refinement_tag_ids: [], selected_tag_ids: [], refinement_catalog_version: "discovery-tags-v1", refinement_round: 0, ambiguities: [], clarification_required: false, parsing_method: "deterministic", semantic_coverage_status: "complete", personalization_enabled: false, source_hints: ["bytedance"],
    created_at: "2026-08-25T00:00:00Z", expires_at: "2026-08-25T01:00:00Z",
  },
};

const result: DiscoveryResult = {
  result_id: "result-1",
  identity: { source: "bytedance", provider: "bytedance", tenant: null, external_job_id: "1", external_job_code: "A1", canonical_url: "https://jobs.bytedance.com/job/1" },
  normalized: {
    company: "字节跳动", role: "AI 产品经理", location: "北京", recruitment_type: "社招",
    source_url: "https://jobs.bytedance.com/job/1", original_jd: "职位描述与职位要求",
    published_date: "2026-08-25",
    structured_jd: { role: "AI 产品经理", company: "字节跳动", location: "北京", recruitment_type: "社招", published_date: "2026-08-25", role_summary: null, key_requirements: [], knowledge_topics: [], responsibilities: [], required_skills: [], preferred_skills: [], ai_requirements: [], product_requirements: [], technical_requirements: [], domain_requirements: [], requirement_taxonomy_version: "legacy-v1", requirements: [], subjective_expectations: [] },
  },
  deterministic_derived: { role_family: "ai_product", role_confidence: "High", explicit_hard_signals: [{ type: "experience_years", operator: ">=", value: 3, display: "明确要求 3+ 年经验", source_text: "至少3年经验" }], content_hash: "hash", dedupe_key: "bytedance:1" },
  search_derived: { relevance_band: "High", matched_constraints: ["北京", "AI Product"], unresolved_constraints: [], excluded_matches: [], reasons: ["北京", "AI Product", "明确要求 3+ 年经验"], reason_items: [{ kind: "matched", code: "location", label: "北京" }, { kind: "warning", code: "experience_years", label: "明确要求 3+ 年经验" }], excluded_by_current_search: false },
  personalization_derived: null,
  in_my_jobs: false, persistent_job_id: null,
};

describe("Phase 7A/B discovery UI", () => {
  it("shows Discover and My Jobs navigation plus an honest empty landing", () => {
    const nav = renderToStaticMarkup(<MemoryRouter><AppNavigation /></MemoryRouter>);
    const landing = renderToStaticMarkup(<MemoryRouter><DiscoverPage /></MemoryRouter>);
    expect(nav).toContain("岗位分析");
    expect(nav).not.toContain(">发现岗位<");
    expect(nav).toContain("我的岗位");
    expect(landing).toContain("今天你想搜索什么机会");
    expect(landing).toContain("个性化推荐：关闭");
    expect(landing).toContain("不读取你的求职档案");
    expect(landing).toContain("个性化推荐：关闭");
  });

  it("renders grounded personalized reasons, risks, and evidence detail", () => {
    const personalized: DiscoveryResult = {
      ...result,
      personalization_derived: {
        band: "Strong",
        candidate_reasons: [{ reason_type: "candidate_evidence_match", display: "存在可支持的 Agent 相关经历", evidence_refs: ["resume_extracted:12"], status: "supported" }],
        candidate_constraint_signals: [{ type: "experience_years", status: "Unknown", display: "当前档案无法确认该经验年限门槛", evidence_refs: [] }],
        evidence: [{ evidence_ref: "resume_extracted:12", source_type: "resume_extracted", text_summary: "Built an Agent workflow", context: "JobPilot" }],
      },
    };
    const html = renderToStaticMarkup(<MemoryRouter><DiscoveryResultCard result={personalized} busy={false} onAdd={() => undefined} /></MemoryRouter>);
    expect(html).toContain("最符合本次目标，也与我的经历相关");
    expect(html).toContain("为什么推荐给我");
    expect(html).toContain("存在可支持的 Agent 相关经历");
    expect(html).toContain("当前档案无法确认");
    expect(html).toContain("resume_extracted:12");
    expect(html).not.toContain("完全匹配");
  });

  it("renders OFF, ON, loading, limited, and unavailable personalization states honestly", () => {
    const off = renderToStaticMarkup(<PersonalizationToggle enabled={false} loading={false} onToggle={() => undefined} />);
    const on = renderToStaticMarkup(<PersonalizationToggle enabled loading={false} message="求职档案信息有限，已仅使用可验证内容进行个性化。" onToggle={() => undefined} />);
    const loading = renderToStaticMarkup(<PersonalizationToggle enabled loading onToggle={() => undefined} />);
    const unavailable = renderToStaticMarkup(<PersonalizationToggle enabled loading={false} message="个性化暂时不可用，当前仍按本次搜索条件展示结果。" onToggle={() => undefined} />);
    expect(off).toContain("个性化推荐：关闭");
    expect(off).toContain("不读取你的求职档案");
    expect(on).toContain("个性化推荐：开启");
    expect(on).toContain("不会改变本次搜索条件");
    expect(on).toContain("信息有限");
    expect(loading).toContain("个性化推荐：加载中");
    expect(unavailable).toContain("个性化暂时不可用");
  });

  it("renders progress, cap, failed, and expired states without fake AI calls", () => {
    const running = renderToStaticMarkup(<DiscoveryProgress session={session} />);
    const capped = renderToStaticMarkup(<DiscoveryProgress session={{ ...session, state: "Partial", result_cap_reached: true, result_count: 500 }} />);
    const failed = renderToStaticMarkup(<DiscoveryProgress session={{ ...session, state: "Failed" }} />);
    const expired = renderToStaticMarkup(<DiscoveryProgress session={{ ...session, state: "Expired" }} />);
    expect(running).toContain("正在搜索岗位");
    expect(running).toContain("Intent Claude calls: 0");
    expect(capped).toContain("超过本次搜索预算");
    expect(failed).toContain("搜索失败");
    expect(expired).toContain("搜索会话已过期");
  });

  it("renders deterministic Why this job and Add/already-added states", () => {
    const available = renderToStaticMarkup(<MemoryRouter><DiscoveryResultCard result={result} busy={false} onAdd={() => undefined} /></MemoryRouter>);
    const added = renderToStaticMarkup(<MemoryRouter><DiscoveryResultCard result={{ ...result, in_my_jobs: true, persistent_job_id: 9 }} busy={false} onAdd={() => undefined} /></MemoryRouter>);
    expect(available).toContain("Why this job");
    expect(available).toContain("✓ 北京");
    expect(available).toContain("⚠ 明确要求 3+ 年经验");
    expect(available).toContain("Add to My Jobs");
    expect(available).not.toContain("适合你本人");
    expect(added).toContain("已加入 My Jobs");
    expect(added).toContain("/jobs/9");
  });

  it("serializes temporary result filters server-side", () => {
    const params = buildDiscoveryParams(2, { location: "北京", company: "字节", role_family: "ai_product", recruitment_type: "campus", relevance: "High", already_in_my_jobs: "false", include_excluded: "true", sort: "published" });
    expect(params.get("page")).toBe("2");
    expect(params.get("location")).toBe("北京");
    expect(params.get("role_family")).toBe("ai_product");
    expect(params.get("recruitment_type")).toBe("campus");
    expect(params.get("already_in_my_jobs")).toBe("false");
    expect(params.get("include_excluded")).toBe("true");
    expect(params.get("sort")).toBe("published");
  });

  it("renders dynamic multi-select refinement and skip controls", () => {
    const refining: DiscoverySession = {
      ...session,
      state: "Ready",
      refinement_groups: [{ id: "ai_direction", label: "你更感兴趣哪些 AI 方向？", multi_select: true, tags: [
        { id: "ai_agent", label: "AI Agent", dimension: "ai_direction", parent_id: null, mutually_exclusive_group: null, sort_order: 10 },
        { id: "ai_platform", label: "AI 平台", dimension: "ai_direction", parent_id: null, mutually_exclusive_group: null, sort_order: 20 },
      ] }],
      optional_refinement_groups: [{ id: "ai_direction", label: "你更感兴趣哪些 AI 方向？", multi_select: true, tags: [
        { id: "ai_agent", label: "AI Agent", dimension: "ai_direction", parent_id: null, mutually_exclusive_group: null, sort_order: 10 },
        { id: "ai_platform", label: "AI 平台", dimension: "ai_direction", parent_id: null, mutually_exclusive_group: null, sort_order: 20 },
      ] }],
    };
    const html = renderToStaticMarkup(<RefinementPanel session={refining} selectedTags={["ai_agent"]} loading={false} onToggle={() => undefined} onSearch={() => undefined} />);
    expect(html).toContain("AI Agent");
    expect(html).toContain("AI 平台");
    expect(html).toContain("selected");
    expect(html).toContain("这些就够了，开始搜索");
    expect(html).not.toContain("应用选择");

    const tags = refining.optional_refinement_groups[0].tags;
    expect(nextRefinementSelection([], tags[0], refining.optional_refinement_groups)).toEqual(["ai_agent"]);
    expect(nextRefinementSelection(["ai_agent"], tags[1], refining.optional_refinement_groups)).toEqual(["ai_agent", "ai_platform"]);
    expect(nextRefinementSelection(["ai_agent", "ai_platform"], tags[0], refining.optional_refinement_groups)).toEqual(["ai_platform"]);
  });

  it("distinguishes required clarification from optional refinement", () => {
    const roleGroup = { id: "role", label: "你想找哪一类 AI 岗位？", multi_select: false, tags: [
      { id: "role_ai_product", label: "AI 产品", dimension: "role", parent_id: null, mutually_exclusive_group: "requested_role", sort_order: 10 },
    ] };
    const required = renderToStaticMarkup(<RefinementPanel session={{ ...session, state: "NeedsClarification", required_refinement_groups: [roleGroup], refinement_groups: [roleGroup] }} selectedTags={[]} loading={false} onToggle={() => undefined} onSearch={() => undefined} />);
    expect(required).toContain("需要先确认一个关键条件");
    expect(required).toContain("这些就够了，开始搜索");
    expect(required).toContain("disabled");
  });

  it("renders generalized semantic refinement without product-specific leakage", () => {
    const investmentGroup = { id: "investment_subdomain", label: "你更关注哪类投资方向？", multi_select: true, required: false, source: "semantic_planner" as const, tags: [
      { id: "semantic:investment:ibd", label: "投资银行 / IBD", dimension: "domain", parent_id: null, mutually_exclusive_group: null, normalized_value: null, freeform_value: "investment_banking", sort_order: 10 },
      { id: "semantic:investment:asset", label: "资产管理", dimension: "domain", parent_id: null, mutually_exclusive_group: null, normalized_value: null, freeform_value: "asset_management", sort_order: 20 },
      { id: "semantic:investment:any", label: "不限方向", dimension: "domain", parent_id: null, mutually_exclusive_group: null, normalized_value: null, freeform_value: "不限", sort_order: 30 },
    ] };
    const html = renderToStaticMarkup(<RefinementPanel session={{ ...session, state: "Ready", optional_refinement_groups: [investmentGroup] }} selectedTags={[]} loading={false} onToggle={() => undefined} onSearch={() => undefined} />);
    expect(html).toContain("你更关注哪类投资方向");
    expect(html).toContain("投资银行 / IBD");
    expect(html).not.toContain("AI Agent");
  });

  it("renders Greenhouse identity, structured exclusion, and partial source failure", () => {
    const greenhouse: DiscoveryResult = {
      ...result,
      identity: { ...result.identity, source: "greenhouse:scaleai", provider: "greenhouse", tenant: "scaleai" },
      normalized: { ...result.normalized, company: "Scale AI" },
      search_derived: { ...result.search_derived, relevance_band: "Low", excluded_matches: ["高级/资深岗位"], excluded_by_current_search: true, reason_items: [{ kind: "excluded", code: "explicit_exclusion", label: "高级/资深岗位" }] },
    };
    const card = renderToStaticMarkup(<MemoryRouter><DiscoveryResultCard result={greenhouse} busy={false} onAdd={() => undefined} /></MemoryRouter>);
    const partial = renderToStaticMarkup(<DiscoveryProgress session={{ ...session, state: "Partial", selected_sources: ["bytedance", "greenhouse:scaleai"], source_progress: [...session.source_progress, { source: "greenhouse:scaleai", provider: "greenhouse", tenant: "scaleai", company: "Scale AI", channel: "public_board", status: "Failed", discovered_count: 0, duration_seconds: 2, error_code: "JOB_SOURCE_UNAVAILABLE" }] }} />);
    expect(card).toContain("Greenhouse · scaleai");
    expect(card).toContain("高级/资深岗位");
    expect(partial).toContain("Scale AI · 暂时失败");
    expect(partial).toContain("已搜索 2 个受支持来源");
    expect(partial).toContain("已搜索字节跳动官方招聘源");
  });

  it("shows canonical ByteDance recruitment channels on cards and filters", () => {
    const campus = renderToStaticMarkup(<MemoryRouter><DiscoveryResultCard result={{ ...result, normalized: { ...result.normalized, recruitment_type: "campus" } }} busy={false} onAdd={() => undefined} /></MemoryRouter>);
    expect(campus).toContain("校招");
    const filters = renderToStaticMarkup(<DiscoveryFiltersBar filters={{ location: "", company: "", role_family: "", recruitment_type: "", relevance: "", already_in_my_jobs: "", include_excluded: "", sort: "relevance" }} onChange={() => undefined} />);
    expect(filters).toContain("招聘类型");
    expect(filters).toContain("全部招聘类型");
    expect(filters).toContain("社招");
  });
});
