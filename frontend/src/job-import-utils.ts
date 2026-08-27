import type { JobImportSession } from "./types";

export function isImportTerminal(status: JobImportSession["status"]): boolean {
  return status === "Completed" || status === "Partial" || status === "Failed";
}

export function importPollDelay(attempt: number): number {
  return attempt < 5 ? 1_000 : 2_000;
}

export function isSupportedByteDanceSearchUrl(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return (
      url.protocol === "https:" &&
      url.hostname === "jobs.bytedance.com" &&
      ["/experienced/position", "/campus/position"].includes(url.pathname.replace(/\/$/, ""))
    );
  } catch {
    return false;
  }
}

type Scheduler = (callback: () => void, delay: number) => number;
type Canceller = (timer: number) => void;

export function startImportPolling(
  fetchSession: () => Promise<JobImportSession>,
  onUpdate: (session: JobImportSession) => void,
  onError: (error: Error) => void,
  schedule: Scheduler = (callback, delay) => window.setTimeout(callback, delay),
  cancel: Canceller = (timer) => window.clearTimeout(timer),
): () => void {
  let active = true;
  let attempt = 0;
  let timer: number | null = null;

  const tick = async () => {
    try {
      const session = await fetchSession();
      if (!active) return;
      onUpdate(session);
      if (isImportTerminal(session.status)) return;
      attempt += 1;
      timer = schedule(() => void tick(), importPollDelay(attempt));
    } catch (cause) {
      if (!active) return;
      onError(cause instanceof Error ? cause : new Error("导入进度读取失败。"));
      attempt += 1;
      timer = schedule(() => void tick(), importPollDelay(attempt));
    }
  };

  timer = schedule(() => void tick(), importPollDelay(attempt));
  return () => {
    active = false;
    if (timer !== null) cancel(timer);
  };
}
