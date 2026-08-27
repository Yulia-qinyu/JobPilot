from dataclasses import dataclass

from app.schemas.discovery import DiscoveryRefinementGroup, DiscoveryRefinementTag

CATALOG_VERSION = "discovery-tags-v1"


@dataclass(frozen=True)
class TagDefinition:
    id: str
    label: str
    dimension: str
    query_terms: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    role_family_hints: tuple[str, ...] = ()
    source_search_terms: tuple[str, ...] = ()
    parent_id: str | None = None
    mutually_exclusive_group: str | None = None
    sort_order: int = 0


TAGS = (
    TagDefinition(
        "role_ai_product",
        "AI 产品",
        "role",
        ("ai产品", "ai 产品", "ai product"),
        role_family_hints=("ai_product",),
        mutually_exclusive_group="requested_role",
        sort_order=10,
    ),
    TagDefinition(
        "role_engineering",
        "AI 工程",
        "role",
        ("ai工程", "ai 工程", "ai engineer"),
        role_family_hints=("engineering",),
        mutually_exclusive_group="requested_role",
        sort_order=20,
    ),
    TagDefinition(
        "role_algorithm",
        "算法 / 研究",
        "role",
        ("算法", "algorithm", "research scientist"),
        role_family_hints=("algorithm",),
        mutually_exclusive_group="requested_role",
        sort_order=30,
    ),
    TagDefinition(
        "role_data_product",
        "数据产品",
        "role",
        ("数据产品", "data product"),
        role_family_hints=("data_product",),
        mutually_exclusive_group="requested_role",
        sort_order=40,
    ),
    TagDefinition(
        "role_platform_product",
        "平台产品",
        "role",
        ("平台产品", "platform product"),
        role_family_hints=("platform_product",),
        mutually_exclusive_group="requested_role",
        sort_order=45,
    ),
    TagDefinition(
        "role_growth_product",
        "增长产品",
        "role",
        ("增长产品", "growth product"),
        role_family_hints=("growth_product",),
        mutually_exclusive_group="requested_role",
        sort_order=46,
    ),
    TagDefinition(
        "role_strategy_product",
        "策略产品",
        "role",
        ("策略产品", "strategy product"),
        role_family_hints=("strategy_product",),
        mutually_exclusive_group="requested_role",
        sort_order=47,
    ),
    TagDefinition(
        "role_general_product",
        "通用产品经理",
        "role",
        ("产品经理", "product manager"),
        role_family_hints=("general_product",),
        mutually_exclusive_group="requested_role",
        sort_order=48,
    ),
    TagDefinition(
        "role_solution",
        "解决方案",
        "role",
        ("解决方案", "solution"),
        role_family_hints=("solution",),
        mutually_exclusive_group="requested_role",
        sort_order=50,
    ),
    TagDefinition(
        "role_operations",
        "运营",
        "role",
        ("运营", "operations"),
        role_family_hints=("product_operations",),
        mutually_exclusive_group="requested_role",
        sort_order=60,
    ),
    TagDefinition(
        "ai_agent",
        "AI Agent",
        "ai_direction",
        ("agent", "智能体"),
        source_search_terms=("Agent",),
        sort_order=10,
    ),
    TagDefinition(
        "llm_application",
        "大模型应用",
        "ai_direction",
        ("大模型", "llm", "生成式ai"),
        source_search_terms=("大模型", "LLM"),
        sort_order=20,
    ),
    TagDefinition(
        "ai_platform",
        "AI 平台",
        "ai_direction",
        ("ai平台", "ai platform", "大模型平台", "llm platform"),
        source_search_terms=("AI 平台",),
        sort_order=30,
    ),
    TagDefinition(
        "ai_data",
        "AI 数据",
        "ai_direction",
        ("ai数据", "数据标注"),
        source_search_terms=("AI 数据",),
        sort_order=40,
    ),
    TagDefinition(
        "model_evaluation",
        "模型评测",
        "ai_direction",
        ("模型评测", "ai evaluation", "评测"),
        source_search_terms=("评测",),
        sort_order=50,
    ),
    TagDefinition(
        "multimodal",
        "多模态",
        "ai_direction",
        ("多模态", "multimodal"),
        source_search_terms=("多模态",),
        sort_order=60,
    ),
    TagDefinition(
        "aigc",
        "AIGC",
        "ai_direction",
        ("aigc", "内容生成"),
        source_search_terms=("AIGC",),
        sort_order=70,
    ),
    TagDefinition(
        "agent_application",
        "Agent Application",
        "agent_subtype",
        ("agent应用",),
        parent_id="ai_agent",
        source_search_terms=("Agent Application",),
        sort_order=10,
    ),
    TagDefinition(
        "agent_platform",
        "Agent Platform",
        "agent_subtype",
        ("agent平台",),
        parent_id="ai_agent",
        source_search_terms=("Agent Platform",),
        sort_order=20,
    ),
    TagDefinition(
        "enterprise_agent",
        "Enterprise Agent",
        "agent_subtype",
        ("企业agent",),
        parent_id="ai_agent",
        source_search_terms=("Enterprise Agent",),
        sort_order=30,
    ),
    TagDefinition(
        "workflow_automation",
        "Workflow / Automation",
        "agent_subtype",
        ("workflow", "automation", "工作流"),
        parent_id="ai_agent",
        source_search_terms=("workflow", "automation"),
        sort_order=40,
    ),
    TagDefinition("ecommerce", "电商", "business_scenario", ("电商", "ecommerce"), sort_order=10),
    TagDefinition(
        "international",
        "出海 / 国际化",
        "business_scenario",
        ("出海", "国际化", "international", "global"),
        sort_order=20,
    ),
    TagDefinition(
        "ads_commercialization",
        "广告 / 商业化",
        "business_scenario",
        ("广告", "商业化", "ads"),
        sort_order=30,
    ),
    TagDefinition(
        "fintech",
        "金融科技",
        "business_scenario",
        ("金融科技", "fintech", "支付"),
        role_family_hints=("fintech_product",),
        sort_order=40,
    ),
    TagDefinition(
        "content_creator",
        "内容 / 创作者",
        "business_scenario",
        ("内容", "创作者", "creator"),
        sort_order=50,
    ),
    TagDefinition(
        "search_recommendation",
        "搜索 / 推荐",
        "business_scenario",
        ("搜索", "推荐", "recommendation"),
        sort_order=60,
    ),
    TagDefinition(
        "enterprise_tob",
        "ToB / 企业服务",
        "business_scenario",
        ("tob", "企业服务", "b2b"),
        sort_order=70,
    ),
    TagDefinition(
        "developer_tools",
        "Developer Tools",
        "business_scenario",
        ("开发者工具", "developer tools"),
        sort_order=80,
    ),
    TagDefinition(
        "graduate",
        "应届 / 校招",
        "seniority",
        ("应届", "校招", "秋招", "校园招聘", "new grad", "graduate", "campus"),
        mutually_exclusive_group="recruitment",
        sort_order=10,
    ),
    TagDefinition(
        "entry_level",
        "初级岗位",
        "seniority",
        ("初级", "entry level", "junior"),
        mutually_exclusive_group="seniority",
        sort_order=20,
    ),
    TagDefinition(
        "no_senior_only",
        "不看高级 / 资深",
        "seniority",
        ("不看高级", "不要高级", "不看资深", "不要资深"),
        sort_order=30,
    ),
    TagDefinition(
        "experienced",
        "社招",
        "seniority",
        ("社招", "社会招聘", "有经验岗位", "experienced"),
        mutually_exclusive_group="recruitment",
        sort_order=40,
    ),
    TagDefinition(
        "exclude_operations",
        "排除运营",
        "exclusion",
        ("不要运营", "排除运营", "不看运营"),
        role_family_hints=("product_operations",),
        sort_order=10,
    ),
    TagDefinition(
        "exclude_solution",
        "排除解决方案",
        "exclusion",
        ("不要解决方案", "排除解决方案", "不看解决方案"),
        role_family_hints=("solution",),
        sort_order=20,
    ),
    TagDefinition(
        "exclude_engineering",
        "排除工程",
        "exclusion",
        ("不要工程", "排除工程", "不看工程"),
        role_family_hints=("engineering",),
        sort_order=30,
    ),
    TagDefinition(
        "exclude_algorithm",
        "排除算法",
        "exclusion",
        ("不要算法", "排除算法", "不看算法"),
        role_family_hints=("algorithm",),
        sort_order=40,
    ),
)


class DiscoveryTagCatalog:
    version = CATALOG_VERSION

    def __init__(self) -> None:
        self._by_id = {tag.id: tag for tag in TAGS}

    def get(self, tag_id: str) -> TagDefinition | None:
        return self._by_id.get(tag_id)

    def validate(self, tag_ids: list[str]) -> list[str]:
        valid = list(dict.fromkeys(tag_id for tag_id in tag_ids if tag_id in self._by_id))
        groups: dict[str, str] = {}
        result: list[str] = []
        for tag_id in valid:
            tag = self._by_id[tag_id]
            group = tag.mutually_exclusive_group
            if group and group in groups:
                continue
            if group:
                groups[group] = tag_id
            result.append(tag_id)
        return result

    def matching_ids(self, text: str) -> list[str]:
        normalized = text.casefold()
        return [
            tag.id
            for tag in TAGS
            if tag.dimension != "role"
            and any(alias.casefold() in normalized for alias in (*tag.query_terms, *tag.aliases))
        ]

    def source_terms(self, tag_ids: list[str]) -> list[str]:
        """Return stable visible search concepts for explicitly matched/selected tags."""
        return list(
            dict.fromkeys(
                term
                for tag_id in self.validate(tag_ids)
                if (tag := self.get(tag_id)) is not None
                and tag.dimension not in {"exclusion", "role", "seniority"}
                for term in (tag.source_search_terms[:1] or tag.query_terms[:1])
            )
        )

    def groups(self, *, parent_id: str | None = None) -> list[DiscoveryRefinementGroup]:
        tags = [tag for tag in TAGS if tag.parent_id == parent_id]
        grouped: dict[str, list[TagDefinition]] = {}
        for tag in tags:
            grouped.setdefault(tag.dimension, []).append(tag)
        labels = {
            "role": "你想找哪一类 AI 岗位？",
            "ai_direction": "你更感兴趣哪些 AI 方向？",
            "business_scenario": "你更关注哪些业务场景？",
            "seniority": "你希望查看哪类招聘？",
            "exclusion": "你希望排除哪些岗位？",
            "agent_subtype": "你更关注哪类 Agent？",
        }
        return [
            DiscoveryRefinementGroup(
                id=dimension,
                label=labels[dimension],
                multi_select=dimension != "role",
                tags=[
                    DiscoveryRefinementTag(
                        id=tag.id,
                        label=tag.label,
                        dimension=tag.dimension,
                        parent_id=tag.parent_id,
                        mutually_exclusive_group=tag.mutually_exclusive_group,
                        sort_order=tag.sort_order,
                    )
                    for tag in sorted(items, key=lambda item: item.sort_order)
                ],
            )
            for dimension, items in grouped.items()
        ]

    def child_groups(self, selected_ids: list[str]) -> list[DiscoveryRefinementGroup]:
        parent = next((tag_id for tag_id in selected_ids if self.groups(parent_id=tag_id)), None)
        return self.groups(parent_id=parent) if parent else []
