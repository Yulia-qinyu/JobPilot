import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AnalysisResults, TaxonomyOverview } from "./AnalyzeJobPage";
import type { FitAnalysisPreview, JobPreview } from "./types";

const preview: JobPreview = {
  company: "字节跳动",
  role: "AI 产品经理",
  location: "北京",
  recruitment_type: "校招",
  published_date: null,
  source_url: null,
  original_jd: "一段用于测试的岗位描述。",
  structured_jd: {
    role: "AI 产品经理",
    company: "字节跳动",
    location: "北京",
    recruitment_type: "校招",
    published_date: null,
    role_summary: null,
    key_requirements: [],
    knowledge_topics: [],
    responsibilities: [],
    required_skills: [],
    preferred_skills: [],
    ai_requirements: [],
    product_requirements: [],
    technical_requirements: [],
    domain_requirements: [],
    requirement_taxonomy_version: "legacy-v1",
    requirements: [],
    subjective_expectations: [],
  },
  parser_model: "m",
  parser_prompt_version: "p",
  parser_schema_version: "s",
  source_content_hash: "h",
};

const baseAnalysis: FitAnalysisPreview = {
  match_score: 70,
  score_status: "available",
  recommendation: "Apply",
  summary: "整体具备相关经历。",
  requirement_matches: [
    {
      requirement_id: "r1",
      requirement_text: "数据分析能力扎实",
      importance: "Important",
      is_hard_requirement: false,
      hard_requirement_category: "none",
      match_status: "Strong",
      reason: "有相关项目经历。",
      confidence: "Medium",
      evidence_sources: [],
    },
  ],
  strengths: [],
  gaps: [],
  suggested_preparation: [
    { title: "补充电商经历", action: "整理一段可核验的分析项目。", priority: "High", requirement_ids: ["r1"] },
  ],
  eligibility_requirements: [],
  knowledge_requirements: [],
  score_basis: { included_requirement_ids: ["r1"], excluded_eligibility_count: 0, excluded_knowledge_count: 0 },
  artifact_token: null,
  artifact_expires_at: null,
};

function renderResults(analysis: FitAnalysisPreview) {
  return renderToStaticMarkup(
    <MemoryRouter>
      <AnalysisResults preview={preview} analysis={analysis} onReset={() => undefined} />
    </MemoryRouter>,
  );
}

describe("AnalyzeJobPage result rendering", () => {
  it("does not white-screen when eligibility_requirements / knowledge_requirements are absent (legacy-v1 / partial response)", () => {
    // Reproduces the reported crash: `analysis.eligibility_requirements.length`
    // on an `undefined` value at AnalyzeJobPage TaxonomyOverview.
    const legacy = { ...baseAnalysis } as Record<string, unknown>;
    delete legacy.eligibility_requirements;
    delete legacy.knowledge_requirements;
    delete legacy.score_basis;

    let html = "";
    expect(() => {
      html = renderResults(legacy as unknown as FitAnalysisPreview);
    }).not.toThrow();

    // Result shell + navigation-bearing page still render.
    expect(html).toContain("AI 产品经理");
    expect(html).toContain("岗位要求");
    expect(html).toContain("匹配分析");
    expect(html).toContain("分析其他岗位");
    expect(html).toContain("analysis-result-container");
    expect(html).toContain("analysis-result-surface");
    expect(html).toContain("analysis-result-body");
    // Remaining valid taxonomy content renders normally.
    expect(html).toContain("数据分析能力扎实");
    expect(html).toContain("履历匹配要求");
    // No fabricated taxonomy sections.
    expect(html).not.toContain("岗位资格");
    expect(html).not.toContain("岗位知识要求");
  });

  it("renders eligibility and knowledge sections when the taxonomy overlays are present", () => {
    const full: FitAnalysisPreview = {
      ...baseAnalysis,
      eligibility_requirements: [
        { requirement_id: "e1", requirement_text: "本科及以上学历", status: "Unknown", evidence_ids: [], reason: "未提供学历证据。" },
      ],
      knowledge_requirements: [
        {
          requirement_id: "k1",
          requirement_text: "了解推荐系统原理",
          source_text: "了解推荐系统原理",
          importance: "Preferred",
          knowledge_topics: ["召回", "排序"],
          score_included: false,
        },
      ],
    };
    const html = renderResults(full);
    expect(html).toContain("岗位资格");
    expect(html).toContain("本科及以上学历");
    expect(html).toContain("岗位知识要求");
    expect(html).toContain("召回");
    expect(html).toContain("数据分析能力扎实");
    expect(html).toContain("70%");
  });

  it("shows the empty matchable state without crashing when there are no scorable requirements", () => {
    const empty: FitAnalysisPreview = {
      ...baseAnalysis,
      match_score: null,
      requirement_matches: [],
      eligibility_requirements: [],
      knowledge_requirements: [],
    };
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <TaxonomyOverview analysis={empty} />
      </MemoryRouter>,
    );
    expect(html).toContain("该岗位没有可由履历证据评分的要求。");
    expect(html).not.toContain("岗位资格");
  });

  it("maps internal requirement ids to readable preparation copy", () => {
    const internalId = "reqv2_8bee5441a1218033";
    const value: FitAnalysisPreview = {
      ...baseAnalysis,
      requirement_matches: [{ ...baseAnalysis.requirement_matches[0], requirement_id: internalId, requirement_text: "具备较强的数据分析能力，对数字敏感" }],
      suggested_preparation: [{ title: `针对${internalId}补充证据`, action: `围绕 ${internalId} 复盘 KPay ETL。`, priority: "High", requirement_ids: [internalId] }],
    };
    const html = renderResults(value);
    expect(html).toContain("具备较强的数据分析能力，对数字敏感");
    expect(html).toContain("复盘 KPay ETL");
    expect(html).not.toContain("reqv2_");
  });
});
