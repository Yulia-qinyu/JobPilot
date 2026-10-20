import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import JobsPage from "./JobsPage";

describe("Application Workspace", () => {
  it("shows the manual workspace without automatic tracking or Match Score filters", () => {
    const html = renderToStaticMarkup(<MemoryRouter><JobsPage /></MemoryRouter>);
    expect(html).not.toContain("立即同步全部");
    expect(html).not.toContain("连接招聘平台");
    expect(html).not.toContain("自动追踪");
    expect(html).toContain("岗位阶段、关键备注与最近进展");
    expect(html).toContain("管理状态");
    expect(html).toContain("地点筛选");
    expect(html).not.toContain("全部匹配状态");
    expect(html).not.toContain("匹配度");
  });
});
