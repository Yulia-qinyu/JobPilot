import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import AddJobPage from "./AddJobPage";

describe("Add Job entry point", () => {
  it("keeps manual URL and JD input without surfacing legacy bulk import", () => {
    const html = renderToStaticMarkup(<MemoryRouter><AddJobPage /></MemoryRouter>);
    expect(html).toContain("岗位链接");
    expect(html).toContain("粘贴 JD");
    expect(html).not.toContain("导入搜索结果");
    expect(html).toContain("解析岗位信息");
  });
});
