import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { JobDangerZone, JobIdentityForm } from "./JobDetailPage";

describe("Job Detail management", () => {
  it("edits user-owned job identity fields without requiring source data", () => {
    const html = renderToStaticMarkup(<JobIdentityForm role="AI 产品经理" company="示例公司" location="北京" saving={false} onRoleChange={() => undefined} onCompanyChange={() => undefined} onLocationChange={() => undefined} onCancel={() => undefined} onSubmit={() => undefined} />);
    expect(html).toContain("岗位名称");
    expect(html).toContain("公司");
    expect(html).toContain("地点");
    expect(html).toContain("保存岗位信息");
    expect(html).toContain("这些信息只更新 JobPilot 内的岗位记录");
  });

  it("keeps deletion in an explicit Job Detail danger zone", () => {
    const html = renderToStaticMarkup(<JobDangerZone jobLabel="示例公司 · AI 产品经理" deleting={false} onDelete={() => undefined} />);
    expect(html).toContain("删除岗位");
    expect(html).toContain("及相关备注");
    expect(html).toContain("仅影响 JobPilot 内的数据");
    expect(html).not.toContain("追踪绑定");
  });
});
