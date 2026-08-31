import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ResumeTailoringPanel, { EvidenceDrawer, TailoredDraftView, TailoringPlanView, TailoringPrerequisite } from "./ResumeTailoringPanel";
import { resumeTailoringApi } from "./api";
import type { ResumeTailoring, TailoredBullet, TailoredDraft } from "./types";

const bullet: TailoredBullet = {
  plan_item_id: "p1", experience_id: 1, original_text: "参与实现 LLM 模块。", tailored_text: "参与交付 LLM 匹配模块。", effective_text: "参与交付 LLM 匹配模块。", action: "Rewrite", evidence_source_ids: ["resume_extracted:1"], requirement_ids: ["r1"], change_summary: "突出岗位相关性", state: "Validated",
  change_kind: "MeaningfulRewrite",
  validation: { references_valid: true, numbers_valid: true, skills_valid: true, ownership_valid: true, entities_valid: true, semantic_supported: true, violations: [] },
};
const tailoring: ResumeTailoring = {
  id: 1, job_id: 2, source_resume_id: 1, status: "DraftReady", plan_confirmed_at: "2026-08-25", accepted_at: null, generation_count: 1, is_stale: false, stale_reasons: [], created_at: "2026-08-25", updated_at: "2026-08-25", validation_results: {}, user_edited_draft: null,
  tailoring_plan: { plan_version: "tailoring-plan-v2", confirmed: true, section_order: ["work_experience", "projects", "education", "skills"], skills_to_include: ["LLM"], relevant_requirements: [{ requirement_id: "r1", text: "LLM 产品交付", importance: "Critical", match_status: "Strong" }], unsupported_requirements: [{ requirement_id: "r2", text: "AWS 认证", importance: "Critical", match_status: "Missing" }], evidence: [{ catalog_id: "resume_extracted:1", source_type: "resume_extracted", source_id: "1", text: "参与实现 LLM 模块。", context: "JobPilot" }], evidence_segments: [], experiences: [{ experience_id: 1, organization: "JobPilot", title: "Product Manager", date_range: "2026", emphasis: "Highlight", coverage_summary: "建议重点突出，覆盖 1 个岗位要求。", bullet_items: [{ plan_item_id: "p1", experience_id: 1, source_fact_id: 1, original_text: bullet.original_text, recommended_action: "Rewrite", effective_action: "Rewrite", omit_confirmed: false, target_requirement_ids: ["r1"], allowed_evidence_ids: ["resume_extracted:1"], allowed_segment_ids: [], context_metadata: { experience_title: "Product Manager", organization: "JobPilot", project_name: "", date_range: "2026" }, reason: "支持核心要求" }] }] },
  generated_draft: { summary: "突出 LLM 产品交付。", education: [], skills: ["LLM"], experiences: [{ experience_id: 1, organization: "JobPilot", title: "Product Manager", date_range: "2026", bullets: [bullet] }] },
};

describe("Resume Tailoring UI", () => {
  it("shows the Phase 3 prerequisite without auto analysis", () => {
    const html = renderToStaticMarkup(<TailoringPrerequisite prerequisite="AnalysisRequired" onGoAnalysis={() => undefined} />);
    expect(html).toContain("请先完成岗位匹配分析");
    expect(html).toContain("前往匹配分析");
  });

  it("shows an explicit unavailable state when the job has no matchable requirements", () => {
    const html = renderToStaticMarkup(<TailoringPrerequisite prerequisite="NoMatchableRequirements" onGoAnalysis={() => undefined} />);
    expect(html).toContain("该岗位暂无可基于履历优化的要求");
    expect(html).not.toContain("前往匹配分析");
  });

  it("shows plan actions, unsupported requirements and omit confirmation", () => {
    const planOnly = { ...tailoring, generated_draft: {} };
    const html = renderToStaticMarkup(<TailoringPlanView tailoring={planOnly} busy={false} onGenerate={() => undefined} />);
    expect(html).toContain("简历优化方案");
    expect(html).toContain("AWS 认证");
    expect(html).toContain("省略");
    expect(html).not.toContain("relevance =");
  });

  it("renders before/after, evidence traceability and validation", () => {
    const html = renderToStaticMarkup(<TailoredDraftView tailoring={tailoring} busy={false} onEdit={() => undefined} onKeep={() => undefined} onValidate={() => undefined} onAccept={() => undefined} onRefreshPlan={() => undefined} />);
    expect(html).toContain("原内容");
    expect(html).toContain("建议修改");
    expect(html).toContain("查看依据");
    expect(html).toContain("已验证");
  });

  it("evidence drawer includes evidence, requirement and guardrail status", () => {
    const html = renderToStaticMarkup(<EvidenceDrawer bullet={bullet} plan={tailoring.tailoring_plan} />);
    expect(html).toContain("resume_extracted:1");
    expect(html).toContain("LLM 产品交付");
    expect(html).toContain("经历背景");
    expect(html).toContain("数字真实性：通过");
  });

  it("renders model keep without pretending there is a tailored rewrite", () => {
    const kept = { ...bullet, state: "KeptOriginal" as const, change_kind: "ModelKeep" as const, action: "Keep" as const };
    const generated = tailoring.generated_draft as TailoredDraft;
    const value: ResumeTailoring = { ...tailoring, generated_draft: { ...generated, experiences: [{ ...generated.experiences[0], bullets: [kept] }] } };
    const html = renderToStaticMarkup(<TailoredDraftView tailoring={value} busy={false} onEdit={() => undefined} onKeep={() => undefined} onValidate={() => undefined} onAccept={() => undefined} onRefreshPlan={() => undefined} />);
    expect(html).toContain("原内容已经较适合该岗位，建议保留");
    expect(html).not.toContain("建议修改");
  });

  it("renders stale and unverified draft states safely", () => {
    const unverified = { ...bullet, state: "Unverified" as const };
    const generated = tailoring.generated_draft as TailoredDraft;
    const value: ResumeTailoring = {
      ...tailoring,
      status: "PendingValidation" as const,
      is_stale: true,
      generated_draft: {
        ...generated,
        experiences: [{ ...generated.experiences[0], bullets: [unverified] }],
      },
    };
    const html = renderToStaticMarkup(<TailoredDraftView tailoring={value} busy={false} onEdit={() => undefined} onKeep={() => undefined} onValidate={() => undefined} onAccept={() => undefined} onRefreshPlan={() => undefined} />);
    expect(html).toContain("当前简历优化已过期");
    expect(html).toContain("用户编辑，尚未验证");
    expect(html).toContain("验证改写");
  });

  it("renders the initial loading state", () => {
    const pending = new Promise<never>(() => undefined);
    const original = resumeTailoringApi.get;
    resumeTailoringApi.get = () => pending;
    try {
      expect(renderToStaticMarkup(<ResumeTailoringPanel jobId={2} onGoAnalysis={() => undefined} />)).toContain("正在读取简历优化");
    } finally {
      resumeTailoringApi.get = original;
    }
  });
});
