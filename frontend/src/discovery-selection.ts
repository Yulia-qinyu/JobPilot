import type { DiscoveryRefinementGroup, DiscoveryRefinementTag } from "./types";

export function nextRefinementSelection(
  current: string[],
  tag: DiscoveryRefinementTag,
  groups: DiscoveryRefinementGroup[],
) {
  if (current.includes(tag.id)) {
    const descendants = new Set(
      groups
        .flatMap((group) => group.tags)
        .filter((item) => item.parent_id === tag.id)
        .map((item) => item.id),
    );
    return current.filter((item) => item !== tag.id && !descendants.has(item));
  }
  const mutuallyExclusiveIds = new Set(
    groups
      .flatMap((group) => group.tags)
      .filter(
        (item) =>
          item.mutually_exclusive_group &&
          item.mutually_exclusive_group === tag.mutually_exclusive_group,
      )
      .map((item) => item.id),
  );
  return [...current.filter((item) => !mutuallyExclusiveIds.has(item)), tag.id];
}
