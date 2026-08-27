import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { JobImportProgress } from "./JobImportPanel";
import type { JobImportSession } from "./types";

const base: JobImportSession = {
  id: 7, source: "bytedance", search_url: "https://jobs.bytedance.com/experienced/position",
  status: "Running", stage: "Importing", discovered_count: 120, processed_count: 82,
  imported_count: 78, updated_count: 1, duplicate_count: 3, failed_count: 0,
  result_job_ids: [], failure_details: [], error_code: null, started_at: null, completed_at: null,
  created_at: "2026-08-23T00:00:00Z", updated_at: "2026-08-23T00:00:00Z",
};

describe("Job import progress presentation", () => {
  it("renders queued and discovering states", () => {
    const queued = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={{ ...base, status: "Queued", stage: "Discovering", discovered_count: 0, processed_count: 0 }} /></MemoryRouter>);
    const discovering = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={{ ...base, stage: "Discovering", processed_count: 0 }} /></MemoryRouter>);
    expect(queued).toContain("等待开始");
    expect(discovering).toContain("正在发现岗位");
  });

  it("renders importing counts", () => {
    const html = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={base} /></MemoryRouter>);
    expect(html).toContain("正在导入岗位");
    expect(html).toContain("82 / 120");
    expect(html).toContain("新增");
    expect(html).toContain("重复");
  });

  it("renders completed, partial and failed states safely", () => {
    const completed = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={{ ...base, status: "Completed", stage: "Completed", processed_count: 120 }} /></MemoryRouter>);
    const partial = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={{ ...base, status: "Partial", stage: "Completed", failed_count: 1 }} /></MemoryRouter>);
    const failed = renderToStaticMarkup(<MemoryRouter><JobImportProgress session={{ ...base, status: "Failed", stage: "Completed", error_code: "JOB_IMPORT_FAILED" }} /></MemoryRouter>);
    expect(completed).toContain("查看本次导入岗位");
    expect(partial).toContain("部分岗位已导入");
    expect(failed).toContain("岗位导入未完成");
  });
});
