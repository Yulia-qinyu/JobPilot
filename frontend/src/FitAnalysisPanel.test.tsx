import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  FitAnalysisEmpty,
  FitAnalysisFailure,
  FitAnalysisLoading,
  FitAnalysisResult,
} from "./FitAnalysisPanel";
import type { FitAnalysis } from "./types";

const analysis: FitAnalysis = {
  id: 1,
  job_id: 2,
  match_score: 82,
  score_status: "available",
  recommendation: "Apply",
  summary: "具备直接 AI 产品证据，但仍需补充 Agent 经验。",
  requirement_matches: [
    {
      requirement_id: "req_ai",
      requirement_text: "AI 产品交付",
      importance: "Critical",
      is_hard_requirement: false,
      hard_requirement_category: "none",
      match_status: "Strong",
      reason: "已有真实上线证据。",
      confidence: "High",
      evidence_sources: [
        {
          source_type: "resume_extracted",
          source_id: "12",
          text: "上线 LLM 产品。",
          context: "Acme · Product Manager",
        },
      ],
    },
    {
      requirement_id: "req_agent",
      requirement_text: "Agent 产品经验",
      importance: "Important",
      is_hard_requirement: false,
      hard_requirement_category: "none",
      match_status: "Missing",
      reason: "未找到 Agent 交付证据。",
      confidence: "High",
      evidence_sources: [],
    },
  ],
  strengths: [
    {
      title: "AI 产品交付",
      explanation: "已有真实上线证据。",
      requirement_ids: ["req_ai"],
      evidence: [
        {
          source_type: "resume_extracted",
          source_id: "12",
          text: "上线 LLM 产品。",
          context: "Acme · Product Manager",
        },
      ],
    },
  ],
  gaps: [
    {
      title: "Agent 产品经验",
      severity: "high",
      requirement_id: "req_agent",
      requirement: "Agent 产品经验",
      explanation: "未找到 Agent 交付证据。",
      evidence_status: "none",
      next_step: "准备 Agent architecture 学习计划。",
      is_hard_requirement: false,
      hard_requirement_category: "none",
    },
  ],
  suggested_preparation: [
    { title: "准备一", action: "行动一", priority: "High", requirement_ids: ["req_agent"] },
    { title: "准备二", action: "行动二", priority: "High", requirement_ids: [] },
    { title: "准备三", action: "行动三", priority: "Medium", requirement_ids: [] },
    { title: "准备四", action: "行动四", priority: "Low", requirement_ids: [] },
  ],
  eligibility_requirements: [],
  knowledge_requirements: [],
  score_basis: { included_requirement_ids: ["req-critical", "req-partial"], excluded_eligibility_count: 0, excluded_knowledge_count: 0 },
  created_at: "2026-08-22T00:00:00Z",
  updated_at: "2026-08-22T00:00:00Z",
};


describe("Phase 3 Fit Analysis presentation", () => {
  it("renders score, Chinese recommendation, strengths, gaps, evidence and top three preparation items", () => {
    const html = renderToStaticMarkup(
      <FitAnalysisResult analysis={analysis} isStale={false} analyzing={false} onReanalyze={() => undefined} />,
    );
    expect(html).toContain("82");
    expect(html).toContain("你的岗位匹配情况");
    expect(html).not.toContain("建议投递");
    expect(html).toContain("核心优势");
    expect(html).toContain("Agent 产品经验");
    expect(html).toContain("上线 LLM 产品");
    expect(html).toContain("匹配");
    expect(html).toContain("暂无匹配证据");
    expect(html).toContain("准备三");
    expect(html).not.toContain("准备四");
    expect(html).toContain("查看更多建议（1）");
    expect(html).toContain("重新分析");
    expect(html).toContain("↻ 重新分析");
    expect(html).toContain("reanalyze-button");
    expect(html).toContain("requirement-evidence-list");
    expect(html).not.toContain("<table");
    expect(html).toContain("判断依据");
  });

  it("does not white-screen when the V2 taxonomy overlays are absent (legacy / partial payload)", () => {
    const legacy = { ...analysis } as Record<string, unknown>;
    delete legacy.eligibility_requirements;
    delete legacy.knowledge_requirements;
    delete legacy.score_basis;
    let html = "";
    expect(() => {
      html = renderToStaticMarkup(
        <FitAnalysisResult
          analysis={legacy as unknown as FitAnalysis}
          isStale={false}
          analyzing={false}
          onReanalyze={() => undefined}
        />,
      );
    }).not.toThrow();
    expect(html).toContain("82"); // score shell still renders
    expect(html).toContain("逐项匹配"); // matchable section still renders
    expect(html).not.toContain("岗位资格"); // no fabricated eligibility section
    expect(html).not.toContain("岗位知识要求"); // no fabricated knowledge section
  });

  it("renders stale, pending, loading and failure states", () => {
    const stale = renderToStaticMarkup(
      <FitAnalysisResult analysis={analysis} isStale analyzing={false} onReanalyze={() => undefined} />,
    );
    const pending = renderToStaticMarkup(<FitAnalysisEmpty analyzing={false} onAnalyze={() => undefined} />);
    const analyzing = renderToStaticMarkup(<FitAnalysisEmpty analyzing onAnalyze={() => undefined} />);
    const loading = renderToStaticMarkup(<FitAnalysisLoading />);
    const failure = renderToStaticMarkup(<FitAnalysisFailure message="AI 服务暂时不可用" />);
    expect(stale).toContain("当前匹配分析可能已过期");
    expect(pending).toContain("分析匹配度");
    expect(analyzing).toContain("正在分析匹配度");
    expect(loading).toContain("正在读取匹配分析");
    expect(failure).toContain("AI 服务暂时不可用");
  });
});
