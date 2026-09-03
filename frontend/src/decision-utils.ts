import type {
  EligibilityStatus,
  FinalDecision,
  PreMatchDecision,
  RoleFamily,
  RolePriority,
  TargetRoleFit,
} from "./types";

export const ROLE_FAMILY_LABELS: Record<RoleFamily, string> = {
  ai_product: "AI 产品",
  fintech_product: "金融科技产品",
  data_product: "数据产品",
  strategy_product: "策略产品",
  platform_product: "平台产品",
  growth_product: "增长产品",
  general_product: "通用产品",
  product_operations: "产品运营",
  solution: "解决方案",
  engineering: "工程",
  algorithm: "算法",
  design: "设计",
  other: "其他",
  unknown: "待完善",
};

export const ROLE_FAMILIES = Object.keys(ROLE_FAMILY_LABELS) as RoleFamily[];

export const ROLE_PRIORITY_LABELS: Record<RolePriority, string> = {
  primary: "主攻",
  secondary: "备选",
  exploratory: "探索",
};

export const ELIGIBILITY_LABELS: Record<EligibilityStatus, string> = {
  Eligible: "未发现明确门槛",
  PossiblyEligible: "存在待确认条件",
  Ineligible: "存在明确门槛",
  Unknown: "暂无法判断",
};

export const ROLE_FIT_LABELS: Record<TargetRoleFit, string> = {
  Primary: "主攻",
  Secondary: "备选",
  Exploratory: "探索",
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
