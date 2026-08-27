import { describe, expect, it } from "vitest";

import { canAddTarget } from "./profile-utils";

describe("target limits", () => {
  it("allows fewer than five targets", () => {
    expect(canAddTarget(4)).toBe(true);
  });

  it("stops at five targets", () => {
    expect(canAddTarget(5)).toBe(false);
  });
});

