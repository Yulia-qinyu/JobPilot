import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TargetRoleCard } from "./ProfilePage";

describe("Target Role profile editor", () => {
  it("keeps an unknown system classification out of the normal user UI", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "PM", priority: "primary", auto_role_family: "unknown", role_family_override: null, effective_role_family: "unknown", role_family: "unknown" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("PM");
    expect(html).toContain("主攻");
    expect(html).not.toContain("分类：");
    expect(html).not.toContain("调整分类");
  });

  it("shows only user-owned role text and priority, not derived metadata", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "教师", priority: "secondary", auto_role_family: "ai_product", role_family_override: null, effective_role_family: "ai_product", role_family: "ai_product" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("教师");
    expect(html).toContain("备选");
    expect(html).not.toContain("role-classification");
    expect(html).not.toContain("分类：");
    expect(html).not.toContain("手动分类");
  });

  it("does not expose an existing manual override in the normal card", () => {
    const html = renderToStaticMarkup(<TargetRoleCard roles={[{ id: 1, name: "法务", priority: "exploratory", auto_role_family: "general_product", role_family_override: "strategy_product", effective_role_family: "strategy_product", role_family: "strategy_product" }]} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("法务");
    expect(html).toContain("探索");
    expect(html).not.toContain("策略产品");
    expect(html).not.toContain("恢复推荐分类");
  });

  it("removes the add controls and explains the five-role limit", () => {
    const roles = Array.from({ length: 5 }, (_, index) => ({ id: index + 1, name: `岗位 ${index + 1}`, priority: "primary" as const, auto_role_family: "general_product" as const, role_family_override: null, effective_role_family: "general_product" as const, role_family: "general_product" as const }));
    const html = renderToStaticMarkup(<TargetRoleCard roles={roles} busy={false} onAdd={() => undefined} onUpdate={() => undefined} onRemove={() => undefined} />);
    expect(html).toContain("已达到 5 个目标岗位上限");
    expect(html).not.toContain("target-role-add");
    expect(html).not.toContain("常见岗位");
  });
});
