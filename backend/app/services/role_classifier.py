import re

from app.db.models import Job
from app.schemas.job_decision import RoleClassification


class RoleClassifier:
    VERSION = "role-rules-v1"

    PRODUCT_MARKERS = re.compile(r"产品|product\s*(?:manager|lead|owner)|\bpm\b", re.IGNORECASE)
    AI_MARKERS = re.compile(
        r"(?<![A-Za-z])ai(?![A-Za-z])|aigc|llm|大模型|人工智能|机器学习产品|agent",
        re.IGNORECASE,
    )
    FINTECH_MARKERS = re.compile(
        r"fintech|金融科技|支付产品|信贷产品|风控产品|保险产品", re.IGNORECASE
    )
    DATA_MARKERS = re.compile(r"数据产品|data\s+product|bi\s+product|数据平台产品", re.IGNORECASE)
    STRATEGY_MARKERS = re.compile(r"策略产品|strategy\s+product|产品策略", re.IGNORECASE)
    PLATFORM_MARKERS = re.compile(
        r"平台产品|platform\s+product|技术产品|technical\s+product|基础设施产品", re.IGNORECASE
    )
    GROWTH_MARKERS = re.compile(r"增长产品|growth\s+product|用户增长产品", re.IGNORECASE)
    PRODUCT_OPS_MARKERS = re.compile(r"产品运营|product\s+operations?|product\s+ops", re.IGNORECASE)
    SOLUTION_MARKERS = re.compile(r"解决方案|solution|售前|pre[- ]?sales", re.IGNORECASE)
    ALGORITHM_MARKERS = re.compile(
        r"算法工程师|算法研究|algorithm|research\s+scientist", re.IGNORECASE
    )
    DESIGN_MARKERS = re.compile(
        r"设计师|视觉设计|交互设计|ux\s+designer|ui\s+designer", re.IGNORECASE
    )
    ENGINEERING_MARKERS = re.compile(
        r"工程师|开发工程|software\s+engineer|developer|研发工程|测试开发|architect", re.IGNORECASE
    )

    def classify(self, job: Job) -> RoleClassification:
        metadata_names = self._metadata_names(job.source_metadata or {})
        title = " ".join(
            value for value in (job.role, self._structured_role(job.structured_jd)) if value
        )
        return self.classify_text(title, metadata_names)

    def classify_text(
        self, title: str, metadata_names: list[str] | None = None
    ) -> RoleClassification:
        metadata_names = metadata_names or []
        context = f"{title} {' '.join(metadata_names)}".strip()
        product_context = bool(self.PRODUCT_MARKERS.search(context)) or any(
            "产品" in item or "product" in item.casefold() for item in metadata_names
        )

        for family, pattern, label in (
            ("algorithm", self.ALGORITHM_MARKERS, "岗位标题明确为算法类"),
            ("design", self.DESIGN_MARKERS, "岗位标题明确为设计类"),
            ("engineering", self.ENGINEERING_MARKERS, "岗位标题明确为工程研发类"),
        ):
            if pattern.search(title) and not product_context:
                return RoleClassification(role_family=family, confidence="High", reasons=[label])

        if self.PRODUCT_OPS_MARKERS.search(context):
            return RoleClassification(
                role_family="product_operations",
                confidence="High",
                reasons=["岗位标题或来源分类明确包含产品运营"],
            )
        if self.SOLUTION_MARKERS.search(context) and not product_context:
            return RoleClassification(
                role_family="solution",
                confidence="High",
                reasons=["岗位标题或来源分类明确为解决方案/售前方向"],
            )
        if not product_context:
            return RoleClassification(
                role_family="unknown",
                confidence="Low",
                reasons=["标题和来源分类不足以确认岗位类型"],
            )

        for family, pattern, label in (
            ("fintech_product", self.FINTECH_MARKERS, "产品岗位包含明确 FinTech 场景"),
            ("data_product", self.DATA_MARKERS, "产品岗位包含明确数据产品语义"),
            ("strategy_product", self.STRATEGY_MARKERS, "产品岗位包含明确策略产品语义"),
            ("platform_product", self.PLATFORM_MARKERS, "产品岗位包含明确平台/技术产品语义"),
            ("growth_product", self.GROWTH_MARKERS, "产品岗位包含明确增长产品语义"),
            ("ai_product", self.AI_MARKERS, "产品岗位包含明确 AI/LLM/AIGC 语义"),
        ):
            if pattern.search(context):
                return RoleClassification(role_family=family, confidence="High", reasons=[label])
        return RoleClassification(
            role_family="general_product",
            confidence="Medium",
            reasons=["来源信息确认属于产品岗位，但不足以可靠细分方向"],
        )

    @staticmethod
    def _structured_role(value: object) -> str:
        if isinstance(value, dict):
            return str(value.get("role") or "")
        return ""

    @staticmethod
    def _metadata_names(metadata: dict) -> list[str]:
        result: list[str] = []
        for key in ("job_category", "job_function", "job_subject"):
            value = metadata.get(key)
            if isinstance(value, dict):
                name = str(value.get("name") or "").strip()
                if name:
                    result.append(name)
        return result
