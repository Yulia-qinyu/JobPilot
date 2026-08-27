import json
import re
from dataclasses import dataclass

from app.schemas.resume_tailoring import (
    BulletValidation,
    ContextMetadata,
    SemanticValidationOutput,
    TailoredBullet,
    TailoringPlan,
)
from app.services.claude_client import ClaudeStructuredClient

SKILL_ALIASES = {
    "llm": {"llm", "large language model", "large language models", "大语言模型", "大模型"},
    "postgresql": {"postgresql", "postgres"},
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
}
KNOWN_TECH = {
    "python",
    "sql",
    "javascript",
    "typescript",
    "react",
    "fastapi",
    "postgresql",
    "mysql",
    "tableau",
    "figma",
    "aws",
    "azure",
    "kubernetes",
    "docker",
    "rag",
    "llm",
    "agent",
    "pytorch",
    "tensorflow",
    "lightgbm",
}


@dataclass(frozen=True)
class GuardrailResult:
    validation: BulletValidation


class ResumeClaimValidator:
    PROMPT_VERSION = "resume-claim-validation-v2"
    SCHEMA_VERSION = "resume-claim-validation-wire-v2"
    GUARDRAIL_VERSION = "resume-claims-v2"

    def __init__(self, client: ClaudeStructuredClient | None = None):
        self.client = client

    def deterministic(
        self,
        bullet: str,
        allowed_evidence: list[str],
        candidate_skills: list[str],
        context_metadata: ContextMetadata | None = None,
    ) -> GuardrailResult:
        evidence_text = " ".join(allowed_evidence)
        context_metadata = context_metadata or ContextMetadata()
        violations: list[str] = []
        numbers_valid = self._numbers(bullet) <= self._numbers(evidence_text)
        if not numbers_valid:
            violations.append("包含证据未支持的新数字或量化范围。")
        skills_valid = self._skills_valid(bullet, evidence_text, candidate_skills)
        if not skills_valid:
            violations.append("包含候选人证据未支持的新技能、技术或证书。")
        ownership_valid = self._ownership_level(bullet) <= self._ownership_level(evidence_text)
        if not ownership_valid:
            violations.append("将参与或执行事实升级为主导、领导或全权负责。")
        entities_valid = self._entities_valid(
            bullet,
            f"{evidence_text} {context_metadata.organization} {context_metadata.project_name}",
        )
        if not entities_valid:
            violations.append("包含证据未支持的新客户、市场、团队或业务范围。")
        return GuardrailResult(
            BulletValidation(
                references_valid=True,
                numbers_valid=numbers_valid,
                skills_valid=skills_valid,
                ownership_valid=ownership_valid,
                entities_valid=entities_valid,
                semantic_supported=False,
                violations=violations,
            )
        )

    def semantic_validate(
        self, bullets: list[TailoredBullet], plan: TailoringPlan
    ) -> SemanticValidationOutput:
        if self.client is None:
            raise RuntimeError("A Claude client is required for semantic validation.")
        evidence = {item.catalog_id: item for item in plan.evidence}
        segments = {item.segment_id: item for item in plan.evidence_segments}
        plan_items = {
            item.plan_item_id: item
            for experience in plan.experiences
            for item in experience.bullet_items
        }
        payload = [
            {
                "plan_item_id": bullet.plan_item_id,
                "candidate_bullet": bullet.tailored_text,
                "claim_evidence": [
                    {
                        "evidence_id": source_id,
                        "parent_source_id": (
                            segments[source_id].parent_source_id
                            if source_id in segments
                            else source_id
                        ),
                        "text": (
                            segments[source_id].text
                            if source_id in segments
                            else evidence[source_id].text
                        ),
                    }
                    for source_id in bullet.evidence_source_ids
                ],
                "context_metadata": plan_items[bullet.plan_item_id].context_metadata.model_dump(
                    mode="json"
                ),
            }
            for bullet in bullets
        ]
        return self.client.generate(
            tool_name="submit_resume_claim_validation",
            output_model=SemanticValidationOutput,
            prompt=f"""Perform one-way claim entailment for each candidate resume bullet.
1. Identify only factual claims actually present in candidate_bullet.
2. Check whether every candidate claim is directly supported by claim_evidence or permitted
   context_metadata.
3. Ignore evidence facts the candidate bullet chooses not to mention. Omission is allowed.
4. Missing evidence content is NOT an unsupported candidate claim. Do not evaluate completeness.
5. Context metadata may support only a direct restatement of title, organization, project name,
   or dates. It cannot support inferred responsibility, accomplishment, scope, leadership,
   team size, or outcome.
6. Unsupported includes candidate text that adds scope, ownership, leadership, causation,
   outcome, customer, market, metric, skill, technology, credential, or team size.
7. Return each unsupported_spans value as an exact verbatim substring that actually appears in
   candidate_bullet. Return an empty list when all candidate claims are supported.
8. Return exactly one result per plan_item_id. Do not rewrite or suggest replacement text.

ITEMS:
{json.dumps(payload, ensure_ascii=False)}
""",
        )

    @staticmethod
    def _numbers(value: str) -> set[str]:
        arabic = re.findall(
            r"(?i)(?:[$¥￥€£]\s*)?\d+(?:\.\d+)?(?:\s*[-–~至到]\s*\d+(?:\.\d+)?)?\s*(?:%|x|倍|万\+?|亿|千|百|人|名|个|家|年|月|天|小时|分钟|秒|元|美元|澳元|users?|customers?|clients?|members?)?",
            value,
        )
        chinese = re.findall(
            r"[零一二两三四五六七八九十百千万亿]+(?:\s*[-–~至到]\s*[零一二两三四五六七八九十百千万亿]+)?\s*(?:人|名|个|家|年|月|天|小时|分钟|秒|元|倍)",
            value,
        )
        return {re.sub(r"\s+", "", item).casefold() for item in arabic + chinese if item.strip()}

    @staticmethod
    def _canonical_skill(value: str) -> str:
        normalized = " ".join(value.casefold().split())
        for canonical, aliases in SKILL_ALIASES.items():
            if normalized in aliases:
                return canonical
        return normalized

    def _skills_valid(self, bullet: str, evidence: str, candidate_skills: list[str]) -> bool:
        allowed = {self._canonical_skill(item) for item in candidate_skills}
        evidence_lower = evidence.casefold()
        allowed.update(self._mentioned_tech(evidence_lower))
        for canonical, aliases in SKILL_ALIASES.items():
            if any(alias in evidence_lower for alias in aliases):
                allowed.add(canonical)
        bullet_lower = bullet.casefold()
        mentioned = self._mentioned_tech(bullet_lower)
        for canonical, aliases in SKILL_ALIASES.items():
            if any(
                re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", bullet_lower)
                for alias in aliases
            ):
                mentioned.add(canonical)
        certifications = re.findall(
            r"(?i)\b(?:pmp|cpa|cfa|cet-?\d|aws certified)\b|证书|认证", bullet
        )
        return mentioned <= allowed and all(
            item.casefold() in evidence_lower for item in certifications
        )

    @staticmethod
    def _mentioned_tech(value: str) -> set[str]:
        return {
            canonical
            for canonical in KNOWN_TECH
            if re.search(rf"(?<![a-z]){re.escape(canonical)}(?![a-z])", value)
        }

    @staticmethod
    def _ownership_level(value: str) -> int:
        lowered = value.casefold()
        if re.search(
            r"主导|领导|全权负责|全面负责|管理(?:了|团队)?|\bled\b|\bowned\b|"
            r"\bmanaged\b|spearheaded",
            lowered,
        ):
            return 3
        if re.search(
            r"实现|完成|推动|负责具体执行|\bbuilt\b|\bimplemented\b|\bdelivered\b|\bexecuted\b",
            lowered,
        ):
            return 2
        if re.search(r"参与|协助|贡献|\bparticipated\b|\bassisted\b|\bcontributed\b", lowered):
            return 1
        return 0

    @staticmethod
    def _entities_valid(bullet: str, evidence: str) -> bool:
        scope_terms = {
            "客户": ("客户", "customer", "client"),
            "市场": ("市场", "market", "region"),
            "团队": ("团队", "team"),
            "营收": ("营收", "revenue"),
            "全球": ("全球", "global", "international"),
        }
        bullet_lower = bullet.casefold()
        evidence_lower = evidence.casefold()
        for aliases in scope_terms.values():
            if any(item in bullet_lower for item in aliases) and not any(
                item in evidence_lower for item in aliases
            ):
                return False
        return True
