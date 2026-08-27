import type {
  EligibilityStatus,
  FinalDecision,
  PreMatchDecision,
  RoleFamily,
  RolePriority,
  TargetRoleFit,
} from "./types";

export const ROLE_FAMILY_LABELS: Record<RoleFamily, string> = {
  ai_product: "AI Product",
  fintech_product: "FinTech Product",
  data_product: "Data Product",
  strategy_product: "Strategy Product",
  platform_product: "Platform Product",
  growth_product: "Growth Product",
  general_product: "General Product",
  product_operations: "Product Operations",
  solution: "Solution",
  engineering: "Engineering",
  algorithm: "Algorithm",
  design: "Design",
  other: "Other",
  unknown: "待完善",
};

export const ROLE_FAMILIES = Object.keys(ROLE_FAMILY_LABELS) as RoleFamily[];

export const ROLE_PRIORITY_LABELS: Record<RolePriority, string> = {
  primary: "Primary",
  secondary: "Secondary",
  exploratory: "Exploratory",
};

export const ELIGIBILITY_LABELS: Record<EligibilityStatus, string> = {
  Eligible: "未发现明确门槛",
  PossiblyEligible: "存在待确认条件",
  Ineligible: "存在明确门槛",
  Unknown: "暂无法判断",
};

export const ROLE_FIT_LABELS: Record<TargetRoleFit, string> = {
  Primary: "Primary",
  Secondary: "Secondary",
  Exploratory: "Exploratory",
  Low: "低相关",
  NotTarget: "非目标",
  Unknown: "待确认",
};

export const PRE_DECISION_LABELS: Record<PreMatchDecision, string> = {
  WorthAnalyzing: "值得分析",
  LowPriority: "低优先级",
  Exclude: "排除",
};

export const FINAL_DECISION_LABELS: Record<FinalDecision, string> = {
  Priority: "优先投递",
  Apply: "建议投递",
  Consider: "可以考虑",
  Skip: "跳过",
};
