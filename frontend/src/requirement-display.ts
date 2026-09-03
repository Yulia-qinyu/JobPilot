import type { PreparationItem, RequirementMatch, TailoringRequirement } from "./types";

const INTERNAL_REQUIREMENT_ID = /req(?:v2)?_[a-z0-9_-]+/gi;

export function requirementTextMap(
  requirements: Array<Pick<RequirementMatch | TailoringRequirement, "requirement_id"> & { requirement_text?: string; text?: string }>,
) {
  return new Map(requirements.map((item) => [item.requirement_id, item.requirement_text ?? item.text ?? ""]));
}

export function linkedRequirementTexts(ids: string[], labels: Map<string, string>) {
  return [...new Set(ids.map((id) => labels.get(id)).filter((value): value is string => Boolean(value)))];
}

export function safeUserCopy(value: string, linkedRequirements: string[] = []) {
  const fallback = linkedRequirements[0] || "相关岗位要求";
  return value.replace(INTERNAL_REQUIREMENT_ID, fallback);
}

export function presentPreparation(item: PreparationItem, matches: RequirementMatch[]) {
  const labels = requirementTextMap(matches);
  const requirements = linkedRequirementTexts(item.requirement_ids, labels);
  return {
    title: safeUserCopy(item.title, requirements),
    action: safeUserCopy(item.action, requirements),
    requirements,
  };
}

export function containsInternalRequirementId(value: string) {
  return /req(?:v2)?_[a-z0-9_-]+/i.test(value);
}
