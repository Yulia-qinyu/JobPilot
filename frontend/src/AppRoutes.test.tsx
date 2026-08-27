import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppNavigation, AppRoutes } from "./App";
import { APP_PATHS } from "./app-route-paths";

function renderAt(path: string) {
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={[path]}>
      <AppNavigation />
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("primary product routes", () => {
  it("renders Analyze Job at both / and /analyze while preserving hidden Discover", () => {
    const home = renderAt("/");
    const analyze = renderAt("/analyze");
    const discover = renderAt("/discover");

    expect(home).toContain("先看看这个岗位适不适合你");
    expect(analyze).toContain("粘贴岗位链接或完整 JD");
    expect(discover).toContain("今天你想搜索什么机会");
    expect(home).not.toContain("发现岗位</a>");
    expect(home).toContain("岗位分析");
    expect(home).not.toContain("Phase 7");
    expect(home).toContain('class="active"');
  });

  it("keeps My Jobs, Profile, legacy jobs, add, and detail routes", () => {
    expect(renderAt("/my-jobs")).toContain("我的岗位");
    expect(renderAt("/plan")).toContain("我的计划");
    expect(renderAt("/profile")).toContain("求职档案");
    expect(APP_PATHS.legacyJobs).toBe("/jobs");
    expect(APP_PATHS.addJob).toBe("/jobs/new");
    expect(APP_PATHS.jobDetail).toBe("/jobs/:id");
    expect(renderAt("/jobs/123")).toContain('class="active" href="/my-jobs"');
  });
});
