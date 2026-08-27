import json

from app.schemas.resume_tailoring import TailoredDraftOutput, TailoringPlan
from app.services.claude_client import ClaudeStructuredClient


class ResumeBulletRewriter:
    PROMPT_VERSION = "resume-tailoring-generation-v2"
    SCHEMA_VERSION = "resume-tailoring-wire-v2"

    def __init__(self, client: ClaudeStructuredClient):
        self.client = client

    def generate(self, plan: TailoringPlan) -> TailoredDraftOutput:
        evidence = {item.catalog_id: item for item in plan.evidence}
        segments = {item.segment_id: item for item in plan.evidence_segments}
        requirements = {item.requirement_id: item for item in plan.relevant_requirements}
        items = []
        for experience in plan.experiences:
            for item in experience.bullet_items:
                if item.effective_action not in {"Rewrite", "Add"}:
                    continue
                items.append(
                    {
                        "plan_item_id": item.plan_item_id,
                        "action": item.effective_action,
                        "original_text": item.original_text,
                        "claim_evidence": (
                            [
                                segments[source_id].model_dump(mode="json")
                                for source_id in item.allowed_segment_ids
                            ]
                            if item.allowed_segment_ids
                            else [
                                {
                                    "segment_id": source_id,
                                    "parent_source_id": source_id,
                                    "text": evidence[source_id].text,
                                }
                                for source_id in item.allowed_evidence_ids
                            ]
                        ),
                        "context_metadata": item.context_metadata.model_dump(mode="json"),
                        "target_requirements": [
                            requirements[requirement_id].model_dump(mode="json")
                            for requirement_id in item.target_requirement_ids
                        ],
                    }
                )
        return self.client.generate(
            tool_name="submit_tailored_resume_bullets",
            output_model=TailoredDraftOutput,
            prompt=f"""Tailor resume bullets using only the supplied candidate evidence.
Return exactly one result for every plan_item_id. Tailoring means selecting the most relevant
supported details, moving the strongest requirement-relevant evidence first, compressing
repetition, omitting unrelated details, and restructuring the sentence when that creates
substantive value. Omission is allowed. Tailoring quality is not measured by textual difference.

Return action=Rewrite only when the result materially improves relevance or clarity. Do not make
a cosmetic rewrite involving only whitespace, punctuation, casing, or formatting. If the original
is already concise and requirement-aligned, return action=Keep and copy original_text exactly into
rewritten_text.

Do not add facts, metrics, numbers, skills, technologies, entities, customers, markets, ownership,
leadership, team size, credentials, or outcomes not explicitly supported by claim_evidence. Never
upgrade participated/contributed into led/owned. Context metadata may be restated directly (for
example, Product Owner -> 担任产品负责人), but it must not be expanded into inferred responsibility,
leadership, scope, accomplishment, team size, or outcome. Use concise resume language in the
original bullet's language. Preserve factual names. requirement_ids MUST copy exact IDs from
target_requirements.

For action=Rewrite, evidence_source_ids MUST cite only exact segment_id values from claim_evidence.
For action=Keep, return the item's permitted evidence IDs unchanged. Cite no other IDs. Add items
are confirmed facts, not permission to invent context.

ITEMS:
{json.dumps(items, ensure_ascii=False)}
""",
        )
