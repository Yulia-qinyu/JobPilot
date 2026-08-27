import { describe, expect, it } from "vitest";

import { APPLICATION_STATUS_LABELS } from "./analysis-utils";
import { jobMatchesFilter, sortJobs } from "./job-utils";
import type { JobListItem } from "./types";

const jobs: JobListItem[] = [
  { id: 1, company: "Zeta", role: "PM", location: null, status: "Interview", match_score: null, source: null, external_job_code: null, created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z" },
  { id: 2, company: "Alpha", role: "AI PM", location: "Sydney", status: "Final Interview", match_score: 82, source: "test", external_job_code: "A2", created_at: "2026-08-21T00:00:00Z", updated_at: "2026-08-21T00:00:00Z" },
  { id: 3, company: "Beta", role: "APM", location: null, status: "Applied", match_score: 60, source: null, external_job_code: null, created_at: "2026-08-19T00:00:00Z", updated_at: "2026-08-19T00:00:00Z" },
];

describe("Job Pool utilities", () => {
  it("groups Interview and Final Interview under the interview filter", () => {
    expect(jobs.filter((job) => jobMatchesFilter(job, "Interview")).map((job) => job.id)).toEqual([1, 2]);
  });

  it("sorts by company, score with null last, and most recent", () => {
    expect(sortJobs(jobs, "company").map((job) => job.id)).toEqual([2, 3, 1]);
    expect(sortJobs(jobs, "match_score").map((job) => job.id)).toEqual([2, 3, 1]);
    expect(sortJobs(jobs, "recent").map((job) => job.id)).toEqual([2, 1, 3]);
  });

  it("keeps the approved Simplified Chinese status labels", () => {
    expect(APPLICATION_STATUS_LABELS.Preparing).toBe("待投递");
    expect(APPLICATION_STATUS_LABELS.OA).toBe("在线测评");
    expect(APPLICATION_STATUS_LABELS["Final Interview"]).toBe("终面中");
  });
});
