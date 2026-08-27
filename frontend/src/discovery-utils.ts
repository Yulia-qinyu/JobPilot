export type DiscoveryFilters = { location: string; company: string; role_family: string; recruitment_type: string; relevance: string; already_in_my_jobs: string; include_excluded: string; sort: string };

export const DISCOVERY_TAG_LABELS: Record<string, string> = {
  ai_agent: "AI Agent", llm_application: "大模型应用", ai_platform: "AI 平台",
  ai_data: "AI 数据", model_evaluation: "模型评测", multimodal: "多模态", aigc: "AIGC",
  ecommerce: "电商", international: "出海 / 国际化", ads_commercialization: "广告 / 商业化",
  fintech: "金融科技", content_creator: "内容 / 创作者", search_recommendation: "搜索 / 推荐",
  enterprise_tob: "ToB / 企业服务", developer_tools: "Developer Tools",
  agent_application: "Agent Application", agent_platform: "Agent Platform",
  enterprise_agent: "Enterprise Agent", workflow_automation: "Workflow / Automation",
};

export function buildDiscoveryParams(page: number, filters: DiscoveryFilters) {
  const params = new URLSearchParams({ page: String(page), page_size: "25", sort: filters.sort });
  Object.entries(filters).forEach(([key, value]) => { if (value && key !== "sort") params.set(key, value); });
  return params;
}
