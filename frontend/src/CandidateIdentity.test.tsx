import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CandidateIdentityCard } from "./ProfilePage";

describe("Candidate recruitment identity", () => {
  it("shows the structured graduation cohort for a graduate candidate", () => {
    const html = renderToStaticMarkup(
      <CandidateIdentityCard
        candidateType="graduate"
        graduationYear={2027}
        busy={false}
        onSave={() => undefined}
      />,
    );
    expect(html).toContain("求职身份");
    expect(html).toContain("应届 / 校招");
    expect(html).toContain("毕业届别");
    expect(html).toContain("2027届");
    expect(html).toContain("毕业届别与学历是两条独立证据");
  });

  it("does not show a graduation selector for experienced recruiting", () => {
    const html = renderToStaticMarkup(
      <CandidateIdentityCard
        candidateType="experienced"
        graduationYear={null}
        busy={false}
        onSave={() => undefined}
      />,
    );
    expect(html).toContain("社招");
    expect(html).not.toContain("aria-label=\"毕业届别\"");
  });
});
