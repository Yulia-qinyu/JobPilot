import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TargetRoleCard } from "./ProfilePage";

describe("Target Role profile editor", () => {
  it("warns users only when automatic classification is unknown", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "PM", priority: "primary", auto_role_family: "unknown", role_family_override: null, effective_role_family: "unknown", role_family: "unknown" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("部分目标岗位暂无法确定分类");
    expect(html).toContain("暂无法确定岗位分类，请确认");
    expect(html).toContain("Primary");
    expect(html).toContain("修改分类");
  });

  it("shows the system classification without requiring a taxonomy selection", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "AI 产品经理", priority: "secondary", auto_role_family: "ai_product", role_family_override: null, effective_role_family: "ai_product", role_family: "ai_product" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).not.toContain("暂无法确定岗位分类");
    expect(html).toContain("系统识别");
    expect(html).toContain("AI Product");
    expect(html).toContain("Secondary");
  });

  it("distinguishes a manual classification override", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "产品经理", priority: "exploratory", auto_role_family: "general_product", role_family_override: "strategy_product", effective_role_family: "strategy_product", role_family: "strategy_product" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("Strategy Product");
    expect(html).toContain("手动修正");
  });
});
