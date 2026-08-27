import { describe, expect, it } from "vitest";

import {
  APPLICATION_STATUS_LABELS,
  ASSESSMENT_LABELS,
  deduplicateItems,
  RECOMMENDATION_LABELS,
  visiblePreparation,
} from "./analysis-utils";

describe("analysis localization", () => {
  it("maps internal enums without changing their API values", () => {
    expect(RECOMMENDATION_LABELS["Strong Apply"]).toBe("强烈建议投递");
    expect(RECOMMENDATION_LABELS.Stretch).toBe("可以尝试");
    expect(ASSESSMENT_LABELS.partial).toBe("部分匹配");
    expect(APPLICATION_STATUS_LABELS["Final Interview"]).toBe("终面中");
  });

  it("removes exact and whitespace-only duplicate gaps", () => {
    expect(deduplicateItems(["缺少 SQL 经验", "  缺少  SQL  经验 ", "缺少行业经验"])).toEqual([
      "缺少 SQL 经验",
      "缺少行业经验",
    ]);
  });

  it("shows only the three highest-priority preparation items by default", () => {
    const items = ["一", "二", "三", "四", "五"];
    expect(visiblePreparation(items, false)).toEqual(["一", "二", "三"]);
    expect(visiblePreparation(items, true)).toEqual(items);
  });
});
