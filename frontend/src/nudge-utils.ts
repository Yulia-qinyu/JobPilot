import type { JobSearchStrategy, Nudge } from "./types";

export const STRATEGY_LABELS: Record<JobSearchStrategy, string> = {
  high_volume: "高频投递",
  focused: "重点冲刺",
  balanced: "平衡模式",
  interview_first: "面试优先",
};

export function nudgeHref(nudge: Nudge): string {
  if (nudge.cta.target) return nudge.cta.target;
  if (nudge.job_id !== null) return `/jobs/${nudge.job_id}`;
  return "/my-jobs";
}
