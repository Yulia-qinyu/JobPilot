import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import PlanningAgentCard from "./PlanningAgentCard";
import type { PlanningToday } from "./types";

const base: PlanningToday = {
  snapshot: null,
  is_stale: false,
  empty_context: false,
  empty_message: null,
  timezone: "Australia/Sydney",
  as_of: "2026-08-27",
  signals: {
    days_since_last_job_added: 2,
    days_since_last_application: 3,
    pending_application_count: 1,
    jobs_ready_to_apply_count: 1,
    jobs_without_tailored_resume_count: 1,
    upcoming_interview_count: 1,
    overdue_plan_count: 0,
    today_plan_load: 1,
    recent_completed_plan_count: 1,
  },
};

const snapshot: NonNullable<PlanningToday["snapshot"]> = {
  id: 9,
  advice_date: "2026-08-27",
  summary: "先准备明天的面试，再推进一个待投岗位。",
  generated_at: "2026-08-27T08:30:00+10:00",
  model: "planning-test",
  input_tokens: 500,
  output_tokens: 120,
  latency_ms: 320,
  status: "Generated",
  items: [{
    id: "interview:4",
    priority: "high",
    action_type: "interview_prep",
    title: "准备明天的面试",
    reason: "明天有一场已记录的面试。",
    related_job_id: 4,
    suggested_plan_type: "interview_prep",
    suggested_date: "2026-08-27",
    added_plan_item_id: null,
  }],
};

describe("PlanningAgentCard", () => {
  it("renders an explicit manual trigger before advice exists", () => {
    const html = renderToStaticMarkup(<PlanningAgentCard planning={base} loading={false} error="" onGenerate={() => undefined} onAddToPlan={() => undefined} />);
    expect(html).toContain("帮我规划今天");
    expect(html).toContain("我会看看你的岗位、计划和最近进度");
    expect(html).not.toContain("准备明天的面试");
  });

  it("renders grounded advice and explicit add-to-plan action", () => {
    const html = renderToStaticMarkup(<PlanningAgentCard planning={{ ...base, snapshot }} loading={false} error="" onGenerate={() => undefined} onAddToPlan={() => undefined} />);
    expect(html).toContain("准备明天的面试");
    expect(html).toContain("明天有一场已记录的面试");
    expect(html).toContain("＋ 加入计划");
    expect(html).toContain("重新规划");
  });

  it("shows stale and empty-context states without implying an automatic call", () => {
    const stale = renderToStaticMarkup(<PlanningAgentCard planning={{ ...base, snapshot, is_stale: true }} loading={false} error="" onGenerate={() => undefined} onAddToPlan={() => undefined} />);
    const empty = renderToStaticMarkup(<PlanningAgentCard planning={{ ...base, empty_context: true, empty_message: "请先添加岗位或计划。" }} loading={false} error="" onGenerate={() => undefined} onAddToPlan={() => undefined} />);
    expect(stale).toContain("你的计划有更新");
    expect(stale).toContain("重新规划");
    expect(empty).toContain("请先添加岗位或计划");
    expect(empty).not.toContain("帮我规划今天</button>");
  });
});
