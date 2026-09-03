import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NudgePanel } from "./NudgeModule";
import { STRATEGY_LABELS, nudgeHref } from "./nudge-utils";
import type { Nudge } from "./types";

function render(node: React.ReactElement) {
  return renderToStaticMarkup(<MemoryRouter>{node}</MemoryRouter>);
}

const jobNudge: Nudge = {
  type: "high_match_stale",
  priority: 1,
  job_id: 7,
  title: "这个匹配值得推进",
  message: "Acme 匹配度 88，已经搁置 5 天，建议推进。",
  reason: { match_score: 88, stale_days: 5, strategy: "balanced" },
  cta: { type: "open_job", target: "/jobs/7" },
};

const poolNudge: Nudge = {
  type: "no_new_jobs",
  priority: 3,
  job_id: null,
  title: "补充新的机会",
  message: "已经 6 天没有新增岗位了，去发现更多机会。",
  reason: { days_since_last_added: 6, threshold_days: 5, strategy: "balanced" },
  cta: { type: "open_discover", target: "/discover" },
};

describe("NudgePanel", () => {
  it("shows a minimal line, not a big empty card, when there are no nudges", () => {
    const html = render(<NudgePanel nudges={[]} strategyLabel="平衡模式" />);
    expect(html).toContain("nudge-module-empty");
    expect(html).not.toContain('aria-label="求职提醒"');
    expect(html).toContain("平衡模式");
  });

  it("renders the strategy-aware header and each nudge with its CTA", () => {
    const html = render(
      <NudgePanel nudges={[jobNudge, poolNudge]} strategyLabel="平衡模式" />,
    );
    expect(html).toContain("2 件事值得处理");
    expect(html).toContain("根据你的「平衡模式」和当前岗位状态整理。");
    expect(html).toContain("这个匹配值得推进");
    expect(html).toContain('href="/jobs/7"');
    expect(html).toContain('href="/discover"');
    expect(html).toContain('data-priority="1"');
  });

  it("falls back to a job link then my-jobs when no explicit cta target", () => {
    expect(nudgeHref({ ...jobNudge, cta: { type: "open_job", target: null } })).toBe("/jobs/7");
    expect(
      nudgeHref({ ...poolNudge, cta: { type: "open_my_jobs", target: null } }),
    ).toBe("/my-jobs");
  });

  it("labels every job-search strategy", () => {
    expect(Object.keys(STRATEGY_LABELS).sort()).toEqual(
      ["balanced", "focused", "high_volume", "interview_first"],
    );
  });
});
