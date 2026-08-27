from dataclasses import dataclass

from app.schemas.discovery import (
    DiscoveryPlannedSource,
    DiscoverySearchContext,
    DiscoverySourcePlan,
)
from app.services.job_sources.catalog import SourceCatalog, SourceCatalogEntry


@dataclass(frozen=True)
class CompanyDefinition:
    company_id: str
    name: str
    aliases: tuple[str, ...]


COMPANY_DIRECTORY = (
    CompanyDefinition("bytedance", "字节跳动", ("字节跳动", "字节", "bytedance", "tiktok")),
    CompanyDefinition("tencent", "腾讯", ("腾讯科技", "腾讯", "tencent")),
    CompanyDefinition("xiaomi", "小米", ("小米科技", "小米", "xiaomi")),
    CompanyDefinition("alibaba", "阿里巴巴", ("阿里巴巴", "阿里", "alibaba")),
    CompanyDefinition("ant", "蚂蚁集团", ("蚂蚁集团", "蚂蚁", "ant group")),
    CompanyDefinition("meituan", "美团", ("美团", "meituan")),
    CompanyDefinition("baidu", "百度", ("百度", "baidu")),
    CompanyDefinition("jd", "京东", ("京东", "jd.com")),
    CompanyDefinition("kuaishou", "快手", ("快手", "kuaishou")),
    CompanyDefinition("didi", "滴滴", ("滴滴出行", "滴滴", "didi")),
    CompanyDefinition("xiaohongshu", "小红书", ("小红书", "xiaohongshu")),
    CompanyDefinition("huawei", "华为", ("华为", "huawei")),
    CompanyDefinition("scale_ai", "Scale AI", ("scale ai", "scaleai")),
    CompanyDefinition("greenhouse", "Greenhouse", ("greenhouse",)),
    CompanyDefinition("anthropic", "Anthropic", ("anthropic", "claude")),
)


class CompanySourceResolver:
    """Resolve company intent separately from deterministic source availability."""

    def __init__(self, catalog: SourceCatalog | None = None):
        self.catalog = catalog or SourceCatalog()
        self._by_id = {item.company_id: item for item in COMPANY_DIRECTORY}

    def match_mentions(self, text: str) -> list[CompanyDefinition]:
        folded = text.casefold()
        matches = [
            item
            for item in COMPANY_DIRECTORY
            if any(alias.casefold() in folded for alias in item.aliases)
        ]
        return list(dict.fromkeys(matches))

    def normalize(self, value: str) -> CompanyDefinition | None:
        folded = value.casefold().strip()
        return next(
            (
                item
                for item in COMPANY_DIRECTORY
                if folded == item.company_id
                or folded == item.name.casefold()
                or any(folded == alias.casefold() for alias in item.aliases)
            ),
            None,
        )

    def plan(self, context: DiscoverySearchContext) -> DiscoverySourcePlan:
        constraints = context.explicit_constraints
        requested: list[str] = []
        requested_labels: dict[str, str] = {}
        for value in constraints.companies:
            item = self.normalize(value)
            company_id = item.company_id if item else f"unresolved:{value.casefold()}"
            requested_labels[company_id] = item.name if item else value
            if company_id not in requested:
                requested.append(company_id)
        entries = list(self.catalog.enabled())
        if requested:
            entries = [entry for entry in entries if entry.company_id in requested]
        else:
            entries = [entry for entry in entries if entry.domestic]
        if not requested and constraints.company_groups:
            groups = set(constraints.company_groups)
            entries = [entry for entry in entries if entry.company_group in groups]

        selected = [
            self._planned(entry, channel)
            for entry in entries
            for channel in self._channels(entry, constraints.recruitment_types)
        ]
        supported_ids = {entry.company_id for entry in entries}
        unsupported_ids = [company_id for company_id in requested if company_id not in supported_ids]
        requested_names = [requested_labels.get(company_id, self._name(company_id)) for company_id in requested]
        unsupported_names = [requested_labels.get(company_id, self._name(company_id)) for company_id in unsupported_ids]
        if not requested:
            status = "supported"
            searched = " · ".join(dict.fromkeys(item.company_name for item in selected))
            message = (
                f"将搜索当前支持的国内招聘源：{searched}。"
                if searched
                else "当前没有可用的国内招聘源。"
            )
        elif selected and unsupported_names:
            status = "partial"
            searched = "、".join(dict.fromkeys(item.company_name for item in selected))
            message = f"将搜索{searched}；{'、'.join(unsupported_names)}官方招聘源暂未支持。"
        elif selected:
            status = "full"
            message = f"将搜索：{' · '.join(dict.fromkeys(item.company_name for item in selected))}。"
        else:
            status = "unsupported"
            message = (
                f"当前暂不支持{'、'.join(unsupported_names or requested_names)}"
                "官方招聘源的批量搜索。"
            )
        return DiscoverySourcePlan(
            requested_companies=requested_names,
            selected_sources=selected,
            unsupported_companies=unsupported_names,
            coverage_status=status,  # type: ignore[arg-type]
            coverage_message=message,
        )

    @staticmethod
    def _channels(entry: SourceCatalogEntry, recruitment_types: list[str]) -> tuple[str, ...]:
        if entry.provider != "bytedance":
            return ("public_board",)
        requested = {value.casefold() for value in recruitment_types}
        graduate = bool(requested & {"graduate", "campus"})
        experienced = bool(requested & {"experienced", "society"})
        if graduate and not experienced:
            return ("campus",)
        if experienced and not graduate:
            return ("experienced",)
        return ("campus", "experienced")

    @staticmethod
    def _planned(entry: SourceCatalogEntry, channel: str) -> DiscoveryPlannedSource:
        return DiscoveryPlannedSource(
            source_key=entry.source_key,
            company_id=entry.company_id,
            company_name=entry.company_name,
            provider=entry.provider,
            channel=channel,
            adapter_key=entry.adapter_key,
            tenant=entry.tenant,
        )

    def _name(self, company_id: str) -> str:
        item = self._by_id.get(company_id)
        return item.name if item else company_id
