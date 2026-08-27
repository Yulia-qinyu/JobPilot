import type { EvidenceItem, JobStatus, Recommendation } from "./types";

export const RECOMMENDATION_LABELS: Record<Recommendation, string> = {
  "Strong Apply": "强烈建议投递",
  Apply: "建议投递",
  Stretch: "可以尝试",
  Skip: "优先级较低",
};

export const REQUIREMENT_MATCH_LABELS = {
  Strong: "匹配",
  Partial: "部分匹配",
  Missing: "暂无匹配证据",
} as const;

export const REQUIREMENT_IMPORTANCE_LABELS = {
  Critical: "核心要求",
  Important: "重要要求",
  Preferred: "加分要求",
} as const;

export const ASSESSMENT_LABELS: Record<EvidenceItem["assessment"], string> = {
  strong: "匹配",
  partial: "部分匹配",
  missing: "暂无匹配证据",
};

export const APPLICATION_STATUS_LABELS: Record<JobStatus, string> = {
  Interested: "感兴趣",
  Preparing: "待投递",
  Applied: "已投递",
  OA: "在线测评",
  Interview: "面试中",
  "Final Interview": "终面中",
  Offer: "Offer",
  Rejected: "未通过",
  Withdrawn: "已撤回",
};

export function visiblePreparation(items: string[], showAll: boolean): string[] {
  return showAll ? items : items.slice(0, 3);
}

export function deduplicateItems(items: string[]): string[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const normalized = item.trim().replace(/\s+/g, " ").toLocaleLowerCase();
    if (!normalized || seen.has(normalized)) return false;
    seen.add(normalized);
    return true;
  });
}
