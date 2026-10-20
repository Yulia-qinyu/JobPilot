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
  it("opens My Jobs at / and keeps Analyze Job at /analyze", () => {
    const home = renderAt("/");
    const analyze = renderAt("/analyze");
    const discover = renderAt("/discover");

    expect(home).toContain("集中查看岗位阶段");
    expect(analyze).toContain("粘贴岗位链接或完整 JD");
    expect(discover).toContain("今天你想搜索什么机会");
    expect(home).not.toContain("发现岗位</a>");
    expect(home).not.toContain(">计划</a>");
    expect(home).not.toContain("招聘平台");
    expect(home).not.toContain("Phase 7");
    expect(home).toContain('class="active"');
  });

  it("keeps My Jobs, Profile, legacy jobs, add, and detail routes", () => {
    expect(renderAt("/my-jobs")).toContain("我的岗位");
    // The standalone planning page is retired; /plan silently redirects.
    expect(renderAt("/plan")).toContain("我的岗位");
    expect(renderAt("/profile")).toContain("求职档案");
    expect(renderAt("/recruiting-platforms")).toContain("我的岗位");
    expect(APP_PATHS.legacyJobs).toBe("/jobs");
    expect(APP_PATHS.addJob).toBe("/jobs/new");
    expect(APP_PATHS.jobDetail).toBe("/jobs/:id");
    expect(renderAt("/jobs/123")).toContain('class="active" href="/my-jobs"');
  });
});
