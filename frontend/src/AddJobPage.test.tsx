import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import AddJobPage from "./AddJobPage";

describe("Add Job entry point", () => {
  it("offers quick add while preserving URL and JD input", () => {
    const html = renderToStaticMarkup(<MemoryRouter><AddJobPage /></MemoryRouter>);
    expect(html).toContain("快速添加");
    expect(html).toContain("岗位链接");
    expect(html).toContain("粘贴 JD");
    expect(html).toContain("岗位名称");
    expect(html).toContain("公司名称");
    expect(html).toContain("投递日期");
    expect(html).toContain("当前状态");
    expect(html).toContain("不会解析 JD 或自动运行匹配分析");
    expect(html).not.toContain("导入搜索结果");
    expect(html).toContain("添加岗位");
  });
});
