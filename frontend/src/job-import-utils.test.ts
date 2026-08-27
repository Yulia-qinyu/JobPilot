import { describe, expect, it, vi } from "vitest";

import { importPollDelay, isImportTerminal, isSupportedByteDanceSearchUrl, startImportPolling } from "./job-import-utils";
import type { JobImportSession } from "./types";

function session(status: JobImportSession["status"]): JobImportSession {
  return {
    id: 1, source: "bytedance", search_url: "https://jobs.bytedance.com/campus/position",
    status, stage: status === "Running" ? "Importing" : "Completed", discovered_count: 120,
    processed_count: status === "Running" ? 20 : 120, imported_count: 100, updated_count: 1,
    duplicate_count: 18, failed_count: 1, result_job_ids: [], failure_details: [], error_code: null,
    started_at: null, completed_at: null, created_at: "2026-08-23T00:00:00Z", updated_at: "2026-08-23T00:00:00Z",
  };
}

describe("Job import utilities", () => {
  it("validates only supported ByteDance search pages", () => {
    expect(isSupportedByteDanceSearchUrl("https://jobs.bytedance.com/experienced/position?location=CT_11")).toBe(true);
    expect(isSupportedByteDanceSearchUrl("https://jobs.bytedance.com/campus/position")).toBe(true);
    expect(isSupportedByteDanceSearchUrl("https://jobs.bytedance.com/referral/position")).toBe(false);
    expect(isSupportedByteDanceSearchUrl("https://evil.example/campus/position")).toBe(false);
  });

  it("recognizes terminal states and polling backoff", () => {
    expect(isImportTerminal("Completed")).toBe(true);
    expect(isImportTerminal("Partial")).toBe(true);
    expect(isImportTerminal("Failed")).toBe(true);
    expect(isImportTerminal("Running")).toBe(false);
    expect(importPollDelay(0)).toBe(1000);
    expect(importPollDelay(5)).toBe(2000);
  });

  it("stops polling on terminal response and cleanup cancels pending polling", async () => {
    const callbacks: Array<() => void> = [];
    const cancelled: number[] = [];
    const schedule = (callback: () => void) => { callbacks.push(callback); return callbacks.length; };
    const updates = vi.fn();
    const fetchTerminal = vi.fn().mockResolvedValue(session("Completed"));
    const stopTerminal = startImportPolling(fetchTerminal, updates, vi.fn(), schedule, (id) => cancelled.push(id));
    callbacks.shift()?.();
    await Promise.resolve();
    expect(fetchTerminal).toHaveBeenCalledOnce();
    expect(callbacks).toHaveLength(0);
    stopTerminal();

    const fetchRunning = vi.fn().mockResolvedValue(session("Running"));
    const stopRunning = startImportPolling(fetchRunning, updates, vi.fn(), schedule, (id) => cancelled.push(id));
    stopRunning();
    expect(cancelled.at(-1)).toBeGreaterThan(0);
  });

  it("keeps polling after a transient progress-read failure", async () => {
    const callbacks: Array<() => void> = [];
    const schedule = (callback: () => void) => { callbacks.push(callback); return callbacks.length; };
    const failure = vi.fn();
    const fetchSession = vi.fn()
      .mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce(session("Completed"));
    const stop = startImportPolling(fetchSession, vi.fn(), failure, schedule, vi.fn());
    callbacks.shift()?.();
    await Promise.resolve();
    expect(failure).toHaveBeenCalledOnce();
    expect(callbacks).toHaveLength(1);
    callbacks.shift()?.();
    await Promise.resolve();
    expect(fetchSession).toHaveBeenCalledTimes(2);
    stop();
  });
});
