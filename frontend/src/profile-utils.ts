export const MAX_TARGETS = 5;

export function canAddTarget(currentCount: number): boolean {
  return currentCount < MAX_TARGETS;
}

export function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
