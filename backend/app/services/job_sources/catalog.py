from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCatalogEntry:
    source_key: str
    company_id: str
    provider: str
    company_name: str
    company_aliases: tuple[str, ...]
    company_group: str
    supported_locations: tuple[str, ...]
    supported_input_kinds: tuple[str, ...]
    adapter_key: str
    tenant: str | None = None
    domestic: bool = True
    enabled: bool = True


SOURCE_CATALOG_VERSION = "discovery-sources-v1"
SOURCE_CATALOG = (
    SourceCatalogEntry(
        source_key="bytedance",
        company_id="bytedance",
        provider="bytedance",
        company_name="字节跳动",
        company_aliases=("字节", "bytedance", "tiktok"),
        company_group="large_tech",
        supported_locations=("北京", "上海", "深圳", "杭州", "广州"),
        supported_input_kinds=("natural_language", "bytedance_search_url"),
        adapter_key="bytedance",
    ),
    SourceCatalogEntry(
        source_key="greenhouse:scaleai",
        company_id="scale_ai",
        provider="greenhouse",
        tenant="scaleai",
        company_name="Scale AI",
        company_aliases=("scale ai", "scaleai"),
        company_group="ai_technology",
        supported_locations=("San Francisco", "New York", "London", "Remote"),
        supported_input_kinds=("natural_language", "greenhouse_board_url"),
        adapter_key="greenhouse",
        enabled=False,
        domestic=False,
    ),
    SourceCatalogEntry(
        source_key="greenhouse:greenhouse",
        company_id="greenhouse",
        provider="greenhouse",
        tenant="greenhouse",
        company_name="Greenhouse",
        company_aliases=("greenhouse",),
        company_group="technology",
        supported_locations=("United States", "Remote"),
        supported_input_kinds=("natural_language", "greenhouse_board_url"),
        adapter_key="greenhouse",
        enabled=False,
        domestic=False,
    ),
    SourceCatalogEntry(
        source_key="greenhouse:anthropic",
        company_id="anthropic",
        provider="greenhouse",
        tenant="anthropic",
        company_name="Anthropic",
        company_aliases=("anthropic", "claude"),
        company_group="ai_technology",
        supported_locations=("San Francisco", "New York", "London", "Remote"),
        supported_input_kinds=("natural_language", "greenhouse_board_url"),
        adapter_key="greenhouse",
        enabled=False,
        domestic=False,
    ),
)


class SourceCatalog:
    version = SOURCE_CATALOG_VERSION

    def __init__(self, *, include_disabled_greenhouse: bool = False):
        self.include_disabled_greenhouse = include_disabled_greenhouse

    def enabled(self) -> list[SourceCatalogEntry]:
        return [
            entry
            for entry in SOURCE_CATALOG
            if entry.enabled
            or (
                self.include_disabled_greenhouse
                and entry.provider == "greenhouse"
                and entry.tenant != "anthropic"
            )
        ]

    def by_key(self, key: str) -> SourceCatalogEntry | None:
        return next((entry for entry in SOURCE_CATALOG if entry.source_key == key), None)

    def by_company_id(self, company_id: str) -> list[SourceCatalogEntry]:
        return [entry for entry in self.enabled() if entry.company_id == company_id]

    def by_tenant(self, tenant: str) -> SourceCatalogEntry | None:
        normalized = tenant.casefold()
        return next(
            (
                entry
                for entry in SOURCE_CATALOG
                if entry.provider == "greenhouse"
                and entry.tenant == normalized
                and (
                    entry.enabled
                    or (self.include_disabled_greenhouse and entry.tenant != "anthropic")
                )
            ),
            None,
        )

    def match_companies(self, text: str) -> list[SourceCatalogEntry]:
        normalized = text.casefold()
        return [
            entry
            for entry in self.enabled()
            if any(alias.casefold() in normalized for alias in entry.company_aliases)
        ]
