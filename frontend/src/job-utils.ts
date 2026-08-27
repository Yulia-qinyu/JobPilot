import type { JobListItem, JobStatus } from "./types";

export const JOB_STATUSES: JobStatus[] = [
  "Interested",
  "Preparing",
  "Applied",
  "OA",
  "Interview",
  "Final Interview",
  "Offer",
  "Rejected",
  "Withdrawn",
];

export function formatJobDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(
    new Date(value),
  );
}

export function formatFullDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(value));
}

export function jobMatchesFilter(job: JobListItem, filter: string): boolean {
  if (filter === "all") return true;
  if (filter === "Interview") {
    return job.status === "Interview" || job.status === "Final Interview";
  }
  return job.status === filter;
}

export function sortJobs(jobs: JobListItem[], sort: string): JobListItem[] {
  const result = [...jobs];
  if (sort === "company") return result.sort((a, b) => a.company.localeCompare(b.company));
  if (sort === "match_score") {
    return result.sort((a, b) => (b.match_score ?? -1) - (a.match_score ?? -1));
  }
  return result.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}
