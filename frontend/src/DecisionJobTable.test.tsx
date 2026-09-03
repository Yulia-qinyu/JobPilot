import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import DecisionJobTable from "./DecisionJobTable";
import type { DecisionJobItem } from "./types";

const base: DecisionJobItem = {
  id: 1,
  company: "ByteDance",
  role: "AI 产品经理",
  location: "北京",
  source: "bytedance",
  status: "Interested",
  created_at: "2026-08-23T00:00:00Z",
  updated_at: "2026-08-23T00:00:00Z",
  match_score: null,
  match_is_stale: false,
  decision: {
    job_id: 1,
    auto_role_family: "ai_product",
    role_family_override: null,
    effective_role_family: "ai_product",
    role_classification_confidence: "High",
    role_classification_reasons: ["标题包含 AI 产品"],
    auto_eligibility_status: "PossiblyEligible",
    eligibility_override: null,
    effective_eligibility_status: "PossiblyEligible",
    eligibility_reasons: ["存在待确认条件"],
    blocking_requirements: [],
    unknown_requirements: ["CET-6"],
    eligibility_override_reason: null,
    target_role_fit: "Primary",
    pre_match_decision: "WorthAnalyzing",
    final_decision: null,
    decision_reasons: ["值得进一步分析"],
    is_stale: false,
    evaluated_at: "2026-08-23T00:00:00Z",
    created_at: "2026-08-23T00:00:00Z",
    updated_at: "2026-08-23T00:00:00Z",
  },
};

describe("My Jobs table", () => {
  it("renders the practical workspace columns without decision language", () => {
    const html = renderToStaticMarkup(<MemoryRouter><DecisionJobTable jobs={[base]} busyId={null} onStatusChange={() => undefined} onDelete={() => undefined} /></MemoryRouter>);
    expect(html).toContain("AI 产品经理");
    expect(html).toContain("ByteDance");
    expect(html).toContain("待分析");
    expect(html).not.toContain("值得分析");
    expect(html).toContain("删除");
  });

  it("keeps Match Score visible and labels stale analysis separately from posting expiry", () => {
    const job = { ...base, match_score: 88, match_is_stale: true, decision: { ...base.decision!, final_decision: "Priority" as const } };
    const html = renderToStaticMarkup(<MemoryRouter><DecisionJobTable jobs={[job]} busyId={null} onStatusChange={() => undefined} onDelete={() => undefined} /></MemoryRouter>);
    expect(html).toContain("88%");
    expect(html).toContain("需更新");
    expect(html).not.toContain("已过期");
    expect(html).not.toContain("优先投递");
  });
});
