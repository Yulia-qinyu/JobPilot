import hashlib
import logging
from datetime import UTC, datetime, timedelta
from math import ceil
from time import perf_counter
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.discovery import (
    AddDiscoveryResultResponse,
    DiscoveryContextUpdate,
    DiscoveryDeterministicDerived,
    DiscoveryExplicitConcept,
    DiscoveryExplicitConstraints,
    DiscoveryIdentity,
    DiscoveryNormalizedJob,
    DiscoveryRefinementGroup,
    DiscoveryRefinementTag,
    DiscoveryResult,
    DiscoveryResultPage,
    DiscoverySearchContext,
    DiscoverySessionRead,
    DiscoverySourcePlan,
    DiscoverySourceProgress,
    DiscoverySourceRaw,
)
from app.services.candidate_discovery_context import (
    CandidateDiscoveryContextError,
    CandidateDiscoveryContextProvider,
    CandidateDiscoveryContextProviderProtocol,
)
from app.services.claude_client import ClaudeStructuredClient
from app.services.discovery_intent import DiscoveryIntentParser
from app.services.discovery_personalization import DiscoveryPersonalizationService
from app.services.discovery_ranking import derive_search_relevance, extract_explicit_hard_signals
from app.services.discovery_source_router import DiscoverySourceRouter, is_url_input
from app.services.discovery_store import DiscoverySessionStore, StoredDiscoverySession
from app.services.discovery_tags import DiscoveryTagCatalog
from app.services.job_sources.base import ImportedJobDraft, SourceJobRecord
from app.services.job_sources.bytedance import JobSourceError
from app.services.job_sources.catalog import SourceCatalog
from app.services.job_sources.registry import JobSourceRegistry
from app.services.role_classifier import RoleClassifier
from app.services.source_acquisition import SourceAcquisitionService
from app.services.workspace_job_upsert import WorkspaceJobUpsertService

logger = logging.getLogger(__name__)
LOCATION_LABELS = {"CT_11": "北京", "CT_12": "上海", "CT_44": "深圳"}
RELEVANCE_ORDER = {"High": 0, "Medium": 1, "Low": 2}


class DiscoveryError(ValueError):
    def __init__(self, message: str, code: str = "DISCOVERY_ERROR"):
        super().__init__(message)
        self.code = code


class DiscoveryService:
    def __init__(
        self,
        db: Session,
        store: DiscoverySessionStore,
        registry: JobSourceRegistry | None = None,
        *,
        settings: Settings | None = None,
        intent_parser: DiscoveryIntentParser | None = None,
        candidate_context_provider: CandidateDiscoveryContextProviderProtocol | None = None,
        source_catalog: SourceCatalog | None = None,
    ):
        self.db = db
        self.store = store
        self.registry = registry
        self.settings = settings
        self.jobs = JobRepository(db)
        self.workspace = WorkspaceJobUpsertService(db)
        self.acquisition = SourceAcquisitionService()
        self.classifier = RoleClassifier()
        self.tags = DiscoveryTagCatalog()
        self.sources = source_catalog or SourceCatalog()
        self.personalizer = DiscoveryPersonalizationService()
        self.candidate_context_provider = candidate_context_provider or (
            CandidateDiscoveryContextProvider(ProfileRepository(db))
        )
        client = (
            ClaudeStructuredClient(settings) if settings and settings.anthropic_api_key else None
        )
        self.intent_parser = intent_parser or DiscoveryIntentParser(client)

    def create_session(self, raw_input: str, personalization_enabled: bool) -> DiscoverySessionRead:
        value = " ".join(raw_input.split())
        now = datetime.now(UTC)
        session_id = str(uuid4())
        if is_url_input(value):
            context, calls, input_tokens, output_tokens = self._url_context(session_id, value, now)
            context = context.model_copy(
                update={"personalization_enabled": personalization_enabled}
            )
            refinement_groups = []
            required_groups = []
            optional_groups = []
            state = "Ready"
        else:
            parsed = self.intent_parser.parse(value)
            context = DiscoverySearchContext(
                session_id=session_id,
                input_kind="natural_language",
                raw_input=value,
                explicit_constraints=parsed.constraints,
                include_terms=parsed.include_terms,
                exclusions=parsed.exclusions,
                freeform_terms=parsed.freeform_terms,
                explicit_concepts=parsed.explicit_concepts,
                explicit_concept_tag_ids=parsed.selected_tag_ids,
                selected_tag_ids=parsed.selected_tag_ids,
                refinement_catalog_version=self.tags.version,
                ambiguities=parsed.ambiguities,
                clarification_required=bool(parsed.required_refinement_dimension_ids),
                parsing_method=parsed.method,
                semantic_coverage_status=parsed.semantic_coverage_status,  # type: ignore[arg-type]
                personalization_enabled=personalization_enabled,
                created_at=now,
                expires_at=now + self._ttl(),
            )
            required_groups = self._merge_groups(
                parsed.required_refinement_groups,
                self._refinement_groups(parsed.required_refinement_dimension_ids),
            )
            optional_groups = self._merge_groups(
                parsed.optional_refinement_groups,
                self._refinement_groups(parsed.optional_refinement_dimension_ids),
            )
            refinement_groups = required_groups or optional_groups
            state = "NeedsClarification" if required_groups else "Ready"
            calls, input_tokens, output_tokens = (
                parsed.claude_calls,
                parsed.input_tokens,
                parsed.output_tokens,
            )
        selected_sources, selected_source_plans, source_plan = self._route_source_names(
            context, allow_empty=state == "NeedsClarification"
        )
        session = DiscoverySessionRead(
            id=session_id,
            state=state,
            search_context=context,
            source=(
                selected_sources[0]
                if len(selected_sources) == 1
                else "multi"
                if selected_sources
                else "unresolved"
            ),
            selected_sources=selected_sources,
            selected_source_plans=selected_source_plans,
            source_plan=source_plan,
            refinement_groups=refinement_groups,
            required_refinement_groups=required_groups,
            optional_refinement_groups=optional_groups,
            claude_api_calls=calls,
            intent_input_tokens=input_tokens,
            intent_output_tokens=output_tokens,
            created_at=now,
            expires_at=context.expires_at,
            personalization_status="Off",
        )
        self.store.create(StoredDiscoverySession(session=session))
        if personalization_enabled:
            session = self._set_personalization(session_id, True)
        logger.info(
            "discovery_session_created session_id=%s input_kind=%s parsing_method=%s "
            "state=%s selected_sources=%s claude_calls=%s",
            session_id,
            context.input_kind,
            context.parsing_method,
            state.lower(),
            len(selected_sources),
            calls,
        )
        return session

    def update_context(
        self, session_id: str, payload: DiscoveryContextUpdate
    ) -> DiscoverySessionRead:
        stored = self.store.get(session_id)
        search_changes = bool(
            payload.selected_tag_ids is not None
            or payload.exclusions is not None
            or payload.skip_refinement
        )
        if payload.personalization_enabled is not None:
            stored.session = self._set_personalization(
                session_id, payload.personalization_enabled
            )
            stored = self.store.get(session_id)
            if not search_changes:
                return stored.session
        if stored.session.state not in {"NeedsClarification", "NeedsRefinement", "Ready"}:
            raise DiscoveryError("当前搜索状态不能修改条件。", "DISCOVERY_INVALID_STATE")
        offered_tags = self._offered_tags(stored.session)
        selected = self._validate_session_selections(
            payload.selected_tag_ids or [], offered_tags
        )
        context = stored.session.search_context
        previous_refinements = list(context.refinement_tag_ids)
        include_terms = self._without_tag_terms(context.include_terms, previous_refinements, False)
        exclusions = list(
            context.exclusions if payload.exclusions is None else payload.exclusions
        )
        if payload.exclusions is None:
            exclusions = self._without_tag_terms(exclusions, previous_refinements, True)
        constraints = context.explicit_constraints.model_copy(deep=True)
        previous_tags = [
            self.tags.get(tag_id) or offered_tags.get(tag_id)
            for tag_id in previous_refinements
        ]
        self._remove_dynamic_refinement_values(constraints, previous_tags)
        previous_recruitment = {
            "graduate" if tag and tag.id == "graduate" else "experienced"
            for tag in previous_tags
            if tag and tag.id in {"graduate", "experienced"}
        }
        constraints.recruitment_types = [
            value
            for value in constraints.recruitment_types
            if value not in previous_recruitment
        ]
        previous_role_hints = {
            family
            for tag in previous_tags
            if tag and hasattr(tag, "role_family_hints") and tag.dimension != "exclusion"
            for family in tag.role_family_hints
        }
        if previous_role_hints:
            constraints.role_families = [
                family
                for family in constraints.role_families
                if family not in previous_role_hints
            ]
        role_selected = any(
            (self.tags.get(tag_id) or offered_tags.get(tag_id)).dimension == "role"
            for tag_id in selected
            if self.tags.get(tag_id) or offered_tags.get(tag_id)
        )
        if role_selected:
            constraints.role_families = []
        for tag_id in selected:
            catalog_tag = self.tags.get(tag_id)
            offered_tag = offered_tags.get(tag_id)
            tag = catalog_tag or offered_tag
            if tag is None:
                continue
            if tag.dimension == "exclusion" or tag.id == "no_senior_only":
                if catalog_tag:
                    exclusions.extend(catalog_tag.query_terms[:1])
            elif tag.dimension not in {"role", "seniority"}:
                if catalog_tag:
                    include_terms.extend(catalog_tag.query_terms[:1])
                elif offered_tag:
                    include_terms.extend(
                        [offered_tag.freeform_value or offered_tag.label]
                    )
            if tag.id == "graduate":
                constraints.recruitment_types = ["graduate"]
            elif tag.id == "experienced":
                constraints.recruitment_types = ["experienced"]
            if catalog_tag:
                for family in catalog_tag.role_family_hints:
                    if family not in constraints.role_families:
                        constraints.role_families.append(family)  # type: ignore[arg-type]
            elif offered_tag:
                self._apply_dynamic_refinement(constraints, offered_tag)
        required_before = bool(stored.session.required_refinement_groups)
        required_tag_ids = {
            tag.id
            for group in stored.session.required_refinement_groups
            for tag in group.tags
        }
        if required_before and not required_tag_ids.intersection(selected):
            raise DiscoveryError(
                "请先选择需要确认的关键搜索条件。", "CLARIFICATION_REQUIRED"
            )
        has_child_selection = any(
            (tag := self.tags.get(tag_id)) is not None and tag.parent_id
            for tag_id in selected
        )
        child_groups = self.tags.child_groups(selected) if not payload.skip_refinement else []
        round_number = 2 if has_child_selection else 1 if child_groups else 0
        updated_context = context.model_copy(
            update={
                "explicit_constraints": constraints,
                "include_terms": list(dict.fromkeys(include_terms)),
                "exclusions": list(dict.fromkeys(exclusions)),
                "refinement_tag_ids": [
                    tag_id
                    for tag_id in selected
                    if (tag := self.tags.get(tag_id) or offered_tags.get(tag_id)) is not None
                    and tag.dimension != "role"
                    and tag_id not in required_tag_ids
                ],
                "selected_tag_ids": list(
                    dict.fromkeys(
                        [
                            *context.explicit_concept_tag_ids,
                            *[
                                tag_id
                                for tag_id in selected
                                if (tag := self.tags.get(tag_id) or offered_tags.get(tag_id)) is not None
                                and tag.dimension != "role"
                                and tag_id not in required_tag_ids
                            ],
                        ]
                    )
                ),
                "refinement_round": round_number,
                "explicit_concepts": [
                    *[
                        item
                        for item in context.explicit_concepts
                        if item.source != "refinement_selection"
                    ],
                    *self._selection_concepts(selected, offered_tags),
                ],
                "ambiguities": [] if required_before else context.ambiguities,
                "clarification_required": False if required_before else context.clarification_required,
            }
        )
        selected_sources, selected_source_plans, source_plan = self._route_source_names(
            updated_context
        )
        if required_before:
            root_optional_groups = list(stored.session.optional_refinement_groups)
        else:
            root_optional_groups = [
                group
                for group in stored.session.optional_refinement_groups
                if all(tag.parent_id is None for tag in group.tags)
            ]
        optional_groups = [
            *root_optional_groups,
            *(
                group
                for group in child_groups
                if group.id not in {item.id for item in root_optional_groups}
            ),
        ]
        stored.session = stored.session.model_copy(
            update={
                "state": "Ready",
                "search_context": updated_context,
                "refinement_groups": optional_groups,
                "required_refinement_groups": [],
                "optional_refinement_groups": optional_groups,
                "selected_sources": selected_sources,
                "selected_source_plans": selected_source_plans,
                "source_plan": source_plan,
                "source": selected_sources[0] if len(selected_sources) == 1 else "multi",
            }
        )
        self.store.save(stored)
        return stored.session

    def get_session(self, session_id: str) -> DiscoverySessionRead:
        return self.store.get(session_id).session

    def search(self, session_id: str) -> None:
        started = perf_counter()
        stored = self.store.get(session_id)
        if stored.session.state != "Ready":
            return
        targets = DiscoverySourceRouter(
            self._registry(), catalog=self.sources
        ).route(stored.session.search_context)
        progress = [
            DiscoverySourceProgress(
                source=target.entry.source_key,
                provider=target.entry.provider,
                tenant=target.entry.tenant,
                company=target.entry.company_name,
                channel=self._public_channel(target.query.channel),
            )
            for target in targets
        ]
        stored.session = stored.session.model_copy(
            update={"state": "Searching", "error_code": None, "source_progress": progress}
        )
        self.store.save(stored)
        records: list[tuple[SourceJobRecord, ImportedJobDraft, str | None]] = []
        failures: list[dict[str, str]] = []
        source_duplicates = 0
        max_results = getattr(self.store, "max_results", 500)
        per_source_budget = max(50, max_results // max(len(targets), 1))
        source_limited = False
        for index, target in enumerate(targets):
            source_started = perf_counter()
            self._update_source_progress(session_id, index, status="Searching")
            try:
                source_total = 0

                def on_page(_offset: int, returned: int, total: int) -> None:
                    nonlocal source_total
                    source_total = max(source_total, total)
                    self._increment_discovered(session_id, returned)

                source_records, duplicates = self.acquisition.discover(
                    target.adapter,
                    target.query,
                    on_page=on_page,
                    max_records=per_source_budget,
                )
                source_limited = source_limited or source_total > len(source_records)
                source_duplicates += duplicates
                for record in source_records:
                    try:
                        records.append(
                            (record, target.adapter.normalize(record), target.entry.company_group)
                        )
                    except ValueError as exc:
                        failures.append(
                            {
                                "source": target.entry.source_key,
                                "error_code": getattr(exc, "code", "INVALID_SOURCE_JOB"),
                            }
                        )
                self._update_source_progress(
                    session_id,
                    index,
                    status="Completed",
                    discovered_count=len(source_records),
                    duration_seconds=perf_counter() - source_started,
                )
            except JobSourceError as exc:
                failures.append({"source": target.entry.source_key, "error_code": exc.code})
                self._update_source_progress(
                    session_id,
                    index,
                    status="Failed",
                    error_code=exc.code,
                    duration_seconds=perf_counter() - source_started,
                )
            except Exception as exc:
                failures.append(
                    {
                        "source": target.entry.source_key,
                        "error_code": "DISCOVERY_INTERNAL_ERROR",
                    }
                )
                self._update_source_progress(
                    session_id,
                    index,
                    status="Failed",
                    error_code="DISCOVERY_INTERNAL_ERROR",
                    duration_seconds=perf_counter() - source_started,
                )
                logger.exception(
                    "discovery_source_failed session_id=%s source=%s exception_type=%s",
                    session_id,
                    target.entry.source_key,
                    type(exc).__name__,
                )

        unique, cross_duplicates = self._dedupe(self._interleave_by_source(records))
        duplicates = source_duplicates + cross_duplicates
        cap_reached = source_limited or len(unique) > max_results
        results: list[DiscoveryResult] = []
        drafts: dict[str, ImportedJobDraft] = {}
        for record, draft, company_group in unique[:max_results]:
            result = self._result(
                stored.session.search_context, record, draft, company_group=company_group
            )
            results.append(result)
            drafts[result.result_id] = draft
        results = self._annotate_my_jobs(results)
        if not results and failures:
            terminal = "Failed"
        elif failures or cap_reached:
            terminal = "Partial"
        else:
            terminal = "Completed"
        current = self.store.get(session_id)
        current.results = results
        current.drafts = drafts
        if current.session.search_context.personalization_enabled:
            current.results = self._personalize_results(current)
        current.session = current.session.model_copy(
            update={
                "state": terminal,
                "processed_count": min(len(unique), max_results),
                "result_count": len(results),
                "duplicate_count": duplicates,
                "failed_count": len(failures),
                "source_failures": failures[:20],
                "error_code": (
                    "DISCOVERY_RESULT_CAP_REACHED"
                    if cap_reached
                    else failures[0]["error_code"]
                    if terminal == "Failed" and failures
                    else None
                ),
                "result_cap_reached": cap_reached,
                "completed_at": datetime.now(UTC),
            }
        )
        self.store.save(current)
        logger.info(
            "discovery_search_completed session_id=%s state=%s sources=%s "
            "duration_seconds=%.3f result_count=%s duplicate_count=%s failed_sources=%s "
            "claude_calls=%s phase3_calls=0",
            session_id,
            terminal.lower(),
            len(targets),
            perf_counter() - started,
            len(results),
            duplicates,
            len([item for item in current.session.source_progress if item.status == "Failed"]),
            current.session.claude_api_calls,
        )

    def result_page(
        self,
        session_id: str,
        *,
        page: int,
        page_size: int,
        location: str | None,
        company: str | None,
        role_family: str | None,
        relevance: str | None,
        already_in_my_jobs: bool | None,
        source: str | None,
        sort: str,
        include_excluded: bool = False,
        recruitment_type: str | None = None,
    ) -> DiscoveryResultPage:
        stored = self.store.get(session_id)
        results = self._annotate_my_jobs(stored.results)
        stored.results = results
        self.store.save(stored)
        if not include_excluded:
            results = [
                item for item in results if not item.search_derived.excluded_by_current_search
            ]
        if location:
            results = [
                item
                for item in results
                if location.casefold() in (item.normalized.location or "").casefold()
            ]
        if company:
            results = [
                item for item in results if company.casefold() in item.normalized.company.casefold()
            ]
        if role_family:
            results = [
                item for item in results if item.deterministic_derived.role_family == role_family
            ]
        if relevance:
            results = [item for item in results if item.search_derived.relevance_band == relevance]
        if already_in_my_jobs is not None:
            results = [item for item in results if item.in_my_jobs is already_in_my_jobs]
        if source:
            results = [item for item in results if item.identity.source == source]
        if recruitment_type:
            results = [
                item
                for item in results
                if item.normalized.recruitment_type == recruitment_type
            ]
        if sort == "published":
            results.sort(
                key=lambda item: (
                    item.normalized.published_date or datetime.min.replace(tzinfo=UTC).date()
                ),
                reverse=True,
            )
        elif sort == "company":
            results.sort(
                key=lambda item: (
                    item.normalized.company.casefold(),
                    item.normalized.role.casefold(),
                )
            )
        else:
            results.sort(key=self._result_sort_key)
        total = len(results)
        start = (page - 1) * page_size
        return DiscoveryResultPage(
            items=results[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def add_to_my_jobs(self, session_id: str, result_id: str) -> AddDiscoveryResultResponse:
        stored = self.store.get(session_id)
        if stored.session.state not in {"Completed", "Partial"}:
            raise DiscoveryError("搜索尚未完成。", "DISCOVERY_NOT_COMPLETE")
        draft = stored.drafts.get(result_id)
        if draft is None:
            raise DiscoveryError("未找到该临时岗位。", "DISCOVERY_RESULT_NOT_FOUND")
        outcome = self.workspace.upsert(draft)
        self.workspace.commit_and_recompute(outcome)
        stored.results = [
            item.model_copy(update={"in_my_jobs": True, "persistent_job_id": outcome.job.id})
            if item.result_id == result_id
            else item
            for item in stored.results
        ]
        self.store.save(stored)
        logger.info(
            "discovery_result_added session_id=%s source=%s external_job_id=%s "
            "outcome=%s job_id=%s claude_calls=0 phase3_calls=0",
            session_id,
            draft.source,
            draft.external_job_id,
            outcome.outcome,
            outcome.job.id,
        )
        return AddDiscoveryResultResponse(outcome=outcome.outcome, persistent_job_id=outcome.job.id)

    def _url_context(
        self, session_id: str, value: str, now: datetime
    ) -> tuple[DiscoverySearchContext, int, None, None]:
        try:
            adapter = self._registry().for_url(value)
        except JobSourceError as exc:
            raise DiscoveryError(
                "当前还不支持从该招聘站批量搜索。你可以粘贴单个岗位链接或 JD。",
                "UNSUPPORTED_JOB_SOURCE_URL",
            ) from exc
        query = adapter.parse_search_url(value)
        if query.provider == "greenhouse":
            entry = self.sources.by_tenant(query.tenant or "")
            constraints = DiscoveryExplicitConstraints(
                companies=[entry.company_name] if entry else []
            )
            kind = "greenhouse_board_url"
        else:
            constraints = DiscoveryExplicitConstraints(
                role_terms=[query.keyword] if query.keyword else [],
                role_families=[
                    family
                    for family in [self.classifier.classify_text(query.keyword).role_family]
                    if family not in {"unknown", "general_product"}
                ],
                locations=[LOCATION_LABELS.get(code, code) for code in query.location_codes],
                companies=["字节跳动"],
                recruitment_types=["experienced" if query.channel == "society" else "graduate"],
            )
            kind = "bytedance_search_url"
        context = DiscoverySearchContext(
            session_id=session_id,
            input_kind=kind,
            raw_input=query.normalized_url,
            explicit_constraints=constraints,
            personalization_enabled=False,
            source_hints=[query.source],
            created_at=now,
            expires_at=now + self._ttl(),
        )
        return context, 0, None, None

    def _result(
        self,
        context: DiscoverySearchContext,
        record: SourceJobRecord,
        draft: ImportedJobDraft,
        *,
        company_group: str | None,
    ) -> DiscoveryResult:
        metadata_names = []
        for key in ("job_category", "job_function", "job_subject"):
            value = draft.source_metadata.get(key)
            if isinstance(value, dict) and value.get("name"):
                metadata_names.append(str(value["name"]))
        metadata_names.extend(str(value) for value in draft.source_metadata.get("departments", []))
        classification = self.classifier.classify_text(draft.role, metadata_names)
        hard_signals = extract_explicit_hard_signals(draft)
        dedupe_key = f"{draft.source}:{draft.external_job_id}"
        result_id = hashlib.sha256(f"{context.session_id}:{dedupe_key}".encode()).hexdigest()[:24]
        return DiscoveryResult(
            result_id=result_id,
            identity=DiscoveryIdentity(
                source=draft.source,
                provider=draft.provider or record.provider or draft.source.split(":", 1)[0],
                tenant=draft.tenant or record.tenant,
                external_job_id=draft.external_job_id,
                external_job_code=draft.external_job_code,
                canonical_url=draft.source_url,
            ),
            source_raw=DiscoverySourceRaw(
                title=record.title,
                locations=list(record.locations),
                recruitment_type=record.recruitment_type,
                description=record.description,
                requirements=record.requirements,
                published_date=record.published_date,
                source_metadata=record.source_metadata,
            ),
            normalized=DiscoveryNormalizedJob(
                company=draft.company,
                role=draft.role,
                location=draft.location,
                recruitment_type=draft.recruitment_type,
                source_url=draft.source_url,
                original_jd=draft.original_jd,
                structured_jd=draft.structured_jd,
                published_date=draft.published_date,
            ),
            deterministic_derived=DiscoveryDeterministicDerived(
                role_family=classification.role_family,
                role_confidence=classification.confidence,
                explicit_hard_signals=hard_signals,
                content_hash=draft.source_content_hash,
                dedupe_key=dedupe_key,
            ),
            search_derived=derive_search_relevance(
                context,
                draft,
                classification.role_family,
                hard_signals,
                company_group=company_group,
            ),
        )

    def _annotate_my_jobs(self, results: list[DiscoveryResult]) -> list[DiscoveryResult]:
        grouped: dict[str, list[str]] = {}
        for result in results:
            grouped.setdefault(result.identity.source, []).append(result.identity.external_job_id)
        existing = {
            (source, external_id): job
            for source, ids in grouped.items()
            for external_id, job in self.jobs.by_source_identities(source, ids).items()
        }
        return [
            item.model_copy(
                update={
                    "in_my_jobs": (item.identity.source, item.identity.external_job_id) in existing,
                    "persistent_job_id": (
                        existing[(item.identity.source, item.identity.external_job_id)].id
                        if (item.identity.source, item.identity.external_job_id) in existing
                        else None
                    ),
                }
            )
            for item in results
        ]

    @staticmethod
    def _dedupe(
        records: list[tuple[SourceJobRecord, ImportedJobDraft, str | None]],
    ) -> tuple[list[tuple[SourceJobRecord, ImportedJobDraft, str | None]], int]:
        identities: set[tuple[str, str]] = set()
        fingerprints: dict[str, str] = {}
        unique = []
        duplicates = 0
        for item in records:
            _, draft, _ = item
            identity = (draft.source, draft.external_job_id)
            fingerprint = "|".join(
                (draft.company.casefold(), draft.role.casefold(), (draft.location or "").casefold())
            )
            same_job_from_other_source = (
                fingerprint in fingerprints and fingerprints[fingerprint] != draft.source
            )
            if identity in identities or same_job_from_other_source:
                duplicates += 1
                continue
            identities.add(identity)
            fingerprints[fingerprint] = draft.source
            unique.append(item)
        return unique, duplicates

    @staticmethod
    def _interleave_by_source(
        records: list[tuple[SourceJobRecord, ImportedJobDraft, str | None]],
    ) -> list[tuple[SourceJobRecord, ImportedJobDraft, str | None]]:
        grouped: dict[str, list[tuple[SourceJobRecord, ImportedJobDraft, str | None]]] = {}
        for item in records:
            grouped.setdefault(item[1].source, []).append(item)
        ordered: list[tuple[SourceJobRecord, ImportedJobDraft, str | None]] = []
        max_length = max((len(items) for items in grouped.values()), default=0)
        for index in range(max_length):
            ordered.extend(items[index] for items in grouped.values() if index < len(items))
        return ordered

    def _increment_discovered(self, session_id: str, returned: int) -> None:
        current = self.store.get(session_id)
        current.session = current.session.model_copy(
            update={"discovered_count": current.session.discovered_count + returned}
        )
        self.store.save(current)

    def _update_source_progress(self, session_id: str, index: int, **updates) -> None:
        current = self.store.get(session_id)
        progress = list(current.session.source_progress)
        progress[index] = progress[index].model_copy(update=updates)
        current.session = current.session.model_copy(update={"source_progress": progress})
        self.store.save(current)

    def _refinement_groups(self, dimension_ids: list[str]):
        return [group for group in self.tags.groups() if group.id in set(dimension_ids)]

    @staticmethod
    def _merge_groups(
        primary: list[DiscoveryRefinementGroup],
        fallback: list[DiscoveryRefinementGroup],
    ) -> list[DiscoveryRefinementGroup]:
        seen: set[str] = set()
        merged: list[DiscoveryRefinementGroup] = []
        for group in [*primary, *fallback]:
            if group.id not in seen:
                seen.add(group.id)
                merged.append(group)
        return merged

    @staticmethod
    def _offered_tags(session: DiscoverySessionRead) -> dict[str, DiscoveryRefinementTag]:
        return {
            tag.id: tag
            for group in [
                *session.required_refinement_groups,
                *session.optional_refinement_groups,
            ]
            for tag in group.tags
        }

    def _validate_session_selections(
        self,
        selected_ids: list[str],
        offered: dict[str, DiscoveryRefinementTag],
    ) -> list[str]:
        selected = list(dict.fromkeys(selected_ids))
        if any(self.tags.get(tag_id) is None and tag_id not in offered for tag_id in selected):
            raise DiscoveryError("包含无效的搜索细化选项。", "INVALID_REFINEMENT_TAG")
        exclusivity: dict[str, str] = {}
        valid: list[str] = []
        for tag_id in selected:
            catalog = self.tags.get(tag_id)
            tag = offered.get(tag_id)
            group = (
                catalog.mutually_exclusive_group
                if catalog is not None
                else tag.mutually_exclusive_group if tag is not None else None
            )
            if group and group in exclusivity:
                continue
            if group:
                exclusivity[group] = tag_id
            valid.append(tag_id)
        return valid

    @staticmethod
    def _remove_dynamic_refinement_values(
        constraints: DiscoveryExplicitConstraints,
        tags: list[object | None],
    ) -> None:
        mapping = {
            "job_function": constraints.job_functions,
            "industry": constraints.industries,
            "domain": constraints.domains,
            "seniority": constraints.seniority,
            "recruitment_type": constraints.recruitment_types,
        }
        for tag in tags:
            if not isinstance(tag, DiscoveryRefinementTag) or tag.normalized_value is None:
                continue
            values = mapping.get(tag.dimension)
            if values is not None:
                values[:] = [value for value in values if value != tag.normalized_value]

    @staticmethod
    def _apply_dynamic_refinement(
        constraints: DiscoveryExplicitConstraints, tag: DiscoveryRefinementTag
    ) -> None:
        if not tag.normalized_value:
            return
        mapping = {
            "job_function": constraints.job_functions,
            "industry": constraints.industries,
            "domain": constraints.domains,
            "seniority": constraints.seniority,
            "recruitment_type": constraints.recruitment_types,
        }
        values = mapping.get(tag.dimension)
        if values is not None and tag.normalized_value not in values:
            values.append(tag.normalized_value)

    def _selection_concepts(
        self,
        selected_ids: list[str],
        offered: dict[str, DiscoveryRefinementTag],
    ) -> list[DiscoveryExplicitConcept]:
        concepts: list[DiscoveryExplicitConcept] = []
        dimension_map = {
            "role": "role_family",
            "ai_direction": "domain",
            "agent_subtype": "domain",
            "business_scenario": "domain",
            "job_function": "job_function",
            "industry": "industry",
            "domain": "domain",
            "seniority": "seniority",
            "recruitment_type": "recruitment_type",
            "exclusion": "other",
        }
        for tag_id in selected_ids:
            catalog = self.tags.get(tag_id)
            dynamic = offered.get(tag_id)
            if catalog is not None:
                normalized = (
                    catalog.role_family_hints[0]
                    if catalog.role_family_hints
                    else catalog.id
                )
                concepts.append(
                    DiscoveryExplicitConcept(
                        raw_text=catalog.label,
                        normalized_id=normalized,
                        dimension=dimension_map.get(catalog.dimension, "other"),  # type: ignore[arg-type]
                        polarity="exclude" if catalog.dimension == "exclusion" else "include",
                        source="refinement_selection",
                    )
                )
            elif dynamic is not None:
                concepts.append(
                    DiscoveryExplicitConcept(
                        raw_text=dynamic.freeform_value or dynamic.label,
                        normalized_id=dynamic.normalized_value,
                        dimension=dimension_map.get(dynamic.dimension, "other"),  # type: ignore[arg-type]
                        source="refinement_selection",
                    )
                )
        return concepts

    def _route_source_names(
        self, context: DiscoverySearchContext, *, allow_empty: bool = False
    ) -> tuple[list[str], list[str], DiscoverySourcePlan]:
        try:
            router = DiscoverySourceRouter(self._registry(), catalog=self.sources)
            plan = router.plan(context)
            names = list(
                dict.fromkeys(target.source_key for target in plan.selected_sources)
            )
            plans = [
                f"{target.source_key}:{target.channel}" for target in plan.selected_sources
            ]
        except ValueError as exc:
            raise DiscoveryError(
                "当前还不支持从该招聘站批量搜索。你可以粘贴单个岗位链接或 JD。",
                "UNSUPPORTED_JOB_SOURCE_URL",
            ) from exc
        if not names and not allow_empty:
            constraints = context.explicit_constraints
            role_labels = {
                "ai_product": "AI Product",
                "fintech_product": "FinTech Product",
                "data_product": "Data Product",
                "strategy_product": "Strategy Product",
                "platform_product": "Platform Product",
                "growth_product": "Growth Product",
                "general_product": "Product",
            }
            understood = [
                *constraints.locations,
                *(role_labels.get(value, value) for value in constraints.role_families),
                *constraints.companies,
            ]
            summary = " · ".join(dict.fromkeys(understood)) or "当前搜索条件"
            company = constraints.companies[0] if constraints.companies else "对应公司"
            message = plan.coverage_message if plan.coverage_status == "unsupported" else ""
            raise DiscoveryError(
                f"已理解：{summary}。{message or f'当前暂不支持{company}官方招聘源的批量搜索。'}"
                "你可以粘贴单个岗位链接或 JD。",
                "NO_SUPPORTED_SOURCES",
            )
        return names, plans, plan

    @staticmethod
    def _public_channel(channel: str) -> str:
        return "experienced" if channel == "society" else channel

    def _without_tag_terms(
        self, values: list[str], tag_ids: list[str], exclusions: bool
    ) -> list[str]:
        removable: set[str] = set()
        for tag_id in tag_ids:
            tag = self.tags.get(tag_id)
            if tag is None:
                continue
            is_exclusion = tag.dimension == "exclusion" or tag.id == "no_senior_only"
            if is_exclusion == exclusions and tag.query_terms:
                removable.add(tag.query_terms[0])
        return [value for value in values if value not in removable]

    def _set_personalization(
        self, session_id: str, enabled: bool
    ) -> DiscoverySessionRead:
        started = perf_counter()
        stored = self.store.get(session_id)
        context = stored.session.search_context.model_copy(
            update={"personalization_enabled": enabled}
        )
        if not enabled:
            stored.personalization_input = None
            stored.results = [self.personalizer.remove(item) for item in stored.results]
            stored.session = stored.session.model_copy(
                update={
                    "search_context": context,
                    "personalization_status": "Off",
                    "personalization_message": None,
                    "personalization_latency_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
            self.store.save(stored)
            return stored.session
        try:
            ranking_input = self.candidate_context_provider.load(context)
            stored.personalization_input = ranking_input
            stored.results = [self.personalizer.apply(item, ranking_input) for item in stored.results]
            limited = ranking_input.candidate_context.limited
            stored.session = stored.session.model_copy(
                update={
                    "search_context": context,
                    "personalization_status": "Limited" if limited else "Ready",
                    "personalization_message": (
                        "求职档案信息有限，已仅使用可验证内容进行个性化。"
                        if limited
                        else "已使用可验证的求职档案与经历证据优化排序和解释。"
                    ),
                    "personalization_latency_ms": round(
                        (perf_counter() - started) * 1000, 3
                    ),
                }
            )
        except (CandidateDiscoveryContextError, SQLAlchemyError, TypeError, ValueError) as exc:
            stored.personalization_input = None
            stored.results = [self.personalizer.remove(item) for item in stored.results]
            stored.session = stored.session.model_copy(
                update={
                    "search_context": context,
                    "personalization_status": "Unavailable",
                    "personalization_message": "个性化暂时不可用，当前仍按本次搜索条件展示结果。",
                    "personalization_latency_ms": round(
                        (perf_counter() - started) * 1000, 3
                    ),
                }
            )
            logger.warning(
                "discovery_personalization_unavailable session_id=%s exception_type=%s",
                session_id,
                type(exc).__name__,
            )
        self.store.save(stored)
        return stored.session

    def _personalize_results(self, stored: StoredDiscoverySession) -> list[DiscoveryResult]:
        if stored.personalization_input is None:
            return stored.results
        return [
            self.personalizer.apply(item, stored.personalization_input)
            for item in stored.results
        ]

    @staticmethod
    def _result_sort_key(item: DiscoveryResult) -> tuple[int, int, int, int]:
        personalized = item.personalization_derived
        personalized_order = {"Strong": 0, "Relevant": 1, "Neutral": 2}
        gap = (
            1
            if personalized
            and any(
                signal.status == "PotentialGap"
                for signal in personalized.candidate_constraint_signals
            )
            else 0
        )
        return (
            RELEVANCE_ORDER[item.search_derived.relevance_band],
            personalized_order.get(personalized.band, 3) if personalized else 3,
            gap,
            -len(personalized.candidate_reasons) if personalized else 0,
        )

    def _ttl(self) -> timedelta:
        return getattr(self.store, "ttl", timedelta(minutes=60))

    def _registry(self) -> JobSourceRegistry:
        if self.registry is None:
            raise RuntimeError("A source registry is required for this operation.")
        return self.registry
