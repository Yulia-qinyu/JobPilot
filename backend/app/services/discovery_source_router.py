from dataclasses import dataclass, replace
from urllib.parse import urlencode, urlsplit

from app.schemas.discovery import (
    DiscoveryPlannedSource,
    DiscoverySearchContext,
    DiscoverySourcePlan,
)
from app.services.company_source_resolver import CompanySourceResolver
from app.services.discovery_tags import DiscoveryTagCatalog
from app.services.job_sources.base import JobSourceAdapter, SourceSearchQuery
from app.services.job_sources.catalog import SourceCatalog, SourceCatalogEntry
from app.services.job_sources.registry import JobSourceRegistry

LOCATION_CODES = {"北京": "CT_11", "上海": "CT_12", "深圳": "CT_44", "杭州": "CT_33"}
DISCOVERY_SOURCE_RESULT_LIMIT = 500


@dataclass(frozen=True)
class DiscoverySourceTarget:
    entry: SourceCatalogEntry
    adapter: JobSourceAdapter
    query: SourceSearchQuery


class DiscoverySourceRouter:
    def __init__(
        self,
        registry: JobSourceRegistry,
        *,
        catalog: SourceCatalog | None = None,
        tags: DiscoveryTagCatalog | None = None,
    ):
        self.registry = registry
        self.catalog = catalog or SourceCatalog()
        self.tags = tags or DiscoveryTagCatalog()
        self.companies = CompanySourceResolver(self.catalog)

    def plan(self, context: DiscoverySearchContext) -> DiscoverySourcePlan:
        if context.input_kind == "natural_language":
            return self.companies.plan(context)
        adapter = self.registry.for_url(context.raw_input)
        query = adapter.parse_search_url(context.raw_input)
        entry = self._entry_for_query(query)
        channel = "experienced" if query.channel == "society" else query.channel
        return DiscoverySourcePlan(
            requested_companies=[entry.company_name],
            selected_sources=[
                DiscoveryPlannedSource(
                    source_key=entry.source_key,
                    company_id=entry.company_id,
                    company_name=entry.company_name,
                    provider=entry.provider,
                    channel=channel,
                    adapter_key=entry.adapter_key,
                    tenant=entry.tenant,
                )
            ],
            coverage_status="full",
            coverage_message=f"将搜索：{entry.company_name}。",
        )

    def route(self, context: DiscoverySearchContext) -> list[DiscoverySourceTarget]:
        if context.input_kind != "natural_language":
            adapter = self.registry.for_url(context.raw_input)
            query = replace(
                adapter.parse_search_url(context.raw_input),
                result_limit=DISCOVERY_SOURCE_RESULT_LIMIT,
            )
            entry = self._entry_for_query(query)
            return [DiscoverySourceTarget(entry, adapter, query)]

        plan = self.companies.plan(context)
        targets: list[DiscoverySourceTarget] = []
        keyword = self._keyword(context)
        for planned in plan.selected_sources:
            entry = self.catalog.by_key(planned.source_key)
            if entry is None:
                continue
            adapter = self.registry.for_query(entry.provider)
            if entry.provider == "bytedance":
                location_codes = [
                    LOCATION_CODES[value]
                    for value in context.explicit_constraints.locations
                    if value in LOCATION_CODES
                ]
                for channel in (planned.channel,):
                    url = f"https://jobs.bytedance.com/{channel}/position"
                    query_string = urlencode(
                        {
                            key: value
                            for key, value in {
                                "keywords": keyword,
                                "location": ",".join(location_codes),
                            }.items()
                            if value
                        }
                    )
                    query = adapter.parse_search_url(
                        f"{url}?{query_string}" if query_string else url
                    )
                    query = replace(query, result_limit=DISCOVERY_SOURCE_RESULT_LIMIT)
                    targets.append(DiscoverySourceTarget(entry, adapter, query))
                continue
            else:
                assert entry.tenant is not None
                query = SourceSearchQuery(
                    source=entry.source_key,
                    normalized_url=f"https://job-boards.greenhouse.io/{entry.tenant}",
                    channel="public_board",
                    keyword=keyword,
                    provider="greenhouse",
                    tenant=entry.tenant,
                )
            targets.append(DiscoverySourceTarget(entry, adapter, query))
        return targets

    def _entry_for_query(self, query: SourceSearchQuery) -> SourceCatalogEntry:
        if query.provider == "greenhouse" and query.tenant:
            entry = self.catalog.by_tenant(query.tenant)
        else:
            entry = self.catalog.by_key("bytedance")
        if entry is None:
            raise ValueError("Supported adapter has no source catalog entry.")
        return entry

    def _keyword(self, context: DiscoverySearchContext) -> str:
        constraints = context.explicit_constraints
        terms = [
            *constraints.role_terms,
            *[
                concept.raw_text
                for concept in context.explicit_concepts
                if concept.polarity == "include"
                and concept.dimension in {"job_function", "industry", "domain", "other"}
            ],
            *context.include_terms,
        ]
        for tag_id in context.selected_tag_ids:
            tag = self.tags.get(tag_id)
            if tag:
                terms.extend(tag.source_search_terms)
        return " ".join(dict.fromkeys(term for term in terms if term.strip()))[:200]


def is_url_input(value: str) -> bool:
    parsed = urlsplit(value.strip())
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
