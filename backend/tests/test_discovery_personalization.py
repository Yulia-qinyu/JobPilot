from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Experience, ExperienceFact, Resume, TargetRole, UserProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import JDRequirements
from app.schemas.discovery import (
    DiscoveryContextUpdate,
    DiscoveryDeterministicDerived,
    DiscoveryExplicitConstraints,
    DiscoveryHardSignal,
    DiscoveryIdentity,
    DiscoveryNormalizedJob,
    DiscoveryResult,
    DiscoverySearchContext,
    DiscoverySearchDerived,
    DiscoverySessionRead,
    DiscoverySourceRaw,
)
from app.schemas.discovery_personalization import (
    CandidateDiscoveryContext,
    CandidateEvidenceItem,
    CandidateEvidenceTopic,
    PersonalizedRankingInput,
    SavedCareerPreferences,
    SavedTargetRole,
)
from app.services.candidate_discovery_context import (
    CandidateDiscoveryContextError,
    CandidateDiscoveryContextProvider,
)
from app.services.discovery_personalization import DiscoveryPersonalizationService
from app.services.discovery_service import DiscoveryService
from app.services.discovery_store import InMemoryDiscoverySessionStore, StoredDiscoverySession


def _context(role_family="ai_product", raw="AI Agent 产品经理"):
    return DiscoverySearchContext(
        session_id="s",
        input_kind="natural_language",
        raw_input=raw,
        explicit_constraints=DiscoveryExplicitConstraints(role_families=[role_family]),
        include_terms=["Agent"],
        selected_tag_ids=["ai_agent"],
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


def _result(title: str, role_family: str, public_band: str = "High", signals=None):
    jd = JDRequirements(role=title, responsibilities=[title])
    return DiscoveryResult(
        result_id=title,
        identity=DiscoveryIdentity(
            source="fixture",
            provider="fixture",
            external_job_id=title,
            canonical_url="https://example.test/job",
        ),
        source_raw=DiscoverySourceRaw(
            title=title,
            locations=["北京"],
            recruitment_type=None,
            description=title,
            requirements="",
            published_date=None,
        ),
        normalized=DiscoveryNormalizedJob(
            company="Example",
            role=title,
            location="北京",
            recruitment_type=None,
            source_url="https://example.test/job",
            original_jd=title,
            structured_jd=jd,
            published_date=None,
        ),
        deterministic_derived=DiscoveryDeterministicDerived(
            role_family=role_family,
            role_confidence="High",
            explicit_hard_signals=signals or [],
            content_hash="hash",
            dedupe_key=title,
        ),
        search_derived=DiscoverySearchDerived(relevance_band=public_band),
    )


def _ranking_input(years=6.0, education=2, role_family="ai_product"):
    evidence = (
        CandidateEvidenceItem(
            "resume_extracted:1",
            "resume_extracted",
            "Designed an AI Agent and LLM product workflow",
            "项目经历",
        ),
        CandidateEvidenceItem(
            "manual_confirmed:2",
            "manual_confirmed",
            "Built a FinTech payment product",
            "KPay",
        ),
    )
    return PersonalizedRankingInput(
        search_context=_context(role_family),
        candidate_context=CandidateDiscoveryContext(
            professional_years=years,
            education_level=education,
            graduation_year=2024,
            evidence=evidence,
            evidence_topics=(
                CandidateEvidenceTopic("ai_product", ("resume_extracted:1",)),
                CandidateEvidenceTopic("agent", ("resume_extracted:1",)),
                CandidateEvidenceTopic("llm", ("resume_extracted:1",)),
                CandidateEvidenceTopic("fintech", ("manual_confirmed:2",)),
            ),
            context_version="v1",
            limited=False,
        ),
        saved_preferences=SavedCareerPreferences(
            target_roles=(
                SavedTargetRole("target_role:1", "AI PM", "primary", "ai_product"),
            ),
            preferred_location="北京",
            target_companies=(),
        ),
    )


def test_candidate_context_admits_only_resume_and_confirmed_manual_evidence() -> None:
    db_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    with Session(db_engine) as db:
        profile = UserProfile(id=1, preferred_location="北京")
        resume = Resume(
            user_profile=profile,
            original_filename="resume.pdf",
            extracted_text="private resume",
            structured_profile={
                "education": [
                    {"institution": "University", "degree": "Bachelor", "period": "2020-2024"}
                ],
                "skills": ["LLM"],
                "work_experience": [
                    {"company": "A", "title": "PM", "period": "2020-2026", "highlights": []}
                ],
            },
        )
        experience = Experience(
            user_profile=profile,
            organization="Project",
            title="Product Manager",
            experience_type="project",
            sort_order=0,
        )
        experience.facts = [
            ExperienceFact(text="Built an AI Agent product", source_type="resume", confirmed=False),
            ExperienceFact(text="Confirmed FinTech work", source_type="manual", confirmed=True),
            ExperienceFact(text="Unconfirmed AWS work", source_type="manual", confirmed=False),
        ]
        profile.target_roles = [
            TargetRole(
                name="AI PM",
                priority="primary",
                auto_role_family="ai_product",
                role_family="ai_product",
            )
        ]
        db.add_all([profile, resume, experience])
        db.commit()
        ranking_input = CandidateDiscoveryContextProvider(ProfileRepository(db)).load(
            _context()
        )
        texts = [item.text for item in ranking_input.candidate_context.evidence]
        assert any("AI Agent" in text for text in texts)
        assert any("Confirmed FinTech" in text for text in texts)
        assert all("Unconfirmed AWS" not in text for text in texts)
        assert {item.source_type for item in ranking_input.candidate_context.evidence} <= {
            "resume_extracted",
            "manual_confirmed",
        }


def test_personalization_cannot_rescue_role_mismatch_or_saved_preference_conflict() -> None:
    service = DiscoveryPersonalizationService()
    ranking_input = _ranking_input()
    agent = service.apply(_result("AI Agent Product Manager", "ai_product"), ranking_input)
    generic = service.apply(_result("AI Product Manager", "ai_product"), ranking_input)
    engineer = service.apply(
        _result("AI Infrastructure Engineer", "engineering", "Low"), ranking_input
    )
    fintech = service.apply(
        _result("FinTech Product Manager", "fintech_product", "Low"), ranking_input
    )
    ordered = sorted(
        [fintech, engineer, generic, agent], key=DiscoveryService._result_sort_key
    )
    assert ordered[0].result_id == "AI Agent Product Manager"
    assert engineer.personalization_derived.band == "Neutral"  # type: ignore[union-attr]
    assert fintech.personalization_derived.band == "Neutral"  # type: ignore[union-attr]
    assert all(
        reason.reason_type != "target_role_alignment"
        for reason in fintech.personalization_derived.candidate_reasons  # type: ignore[union-attr]
    )


def test_current_search_role_precedence_over_saved_target_role() -> None:
    ranking_input = _ranking_input(role_family="fintech_product")
    ranking_input = PersonalizedRankingInput(
        search_context=_context("fintech_product", "上海 FinTech Product"),
        candidate_context=ranking_input.candidate_context,
        saved_preferences=ranking_input.saved_preferences,
    )
    fintech = DiscoveryPersonalizationService().apply(
        _result("Shanghai FinTech Product Manager", "fintech_product"), ranking_input
    )
    ai = DiscoveryPersonalizationService().apply(
        _result("Beijing AI Product Manager", "ai_product", "Low"), ranking_input
    )
    assert fintech.personalization_derived.band == "Strong"  # type: ignore[union-attr]
    assert ai.personalization_derived.band == "Neutral"  # type: ignore[union-attr]
    assert not any(
        reason.reason_type == "target_role_alignment"
        for reason in ai.personalization_derived.candidate_reasons  # type: ignore[union-attr]
    )


def test_generalized_non_product_function_ignores_saved_ai_product_target() -> None:
    base = _ranking_input()
    search_context = _context("unknown", "北京 银行 应届 投资").model_copy(
        update={
            "explicit_constraints": DiscoveryExplicitConstraints(
                locations=["北京"],
                job_functions=["investment"],
                industries=["banking"],
                recruitment_types=["graduate"],
            )
        }
    )
    ranking_input = PersonalizedRankingInput(
        search_context=search_context,
        candidate_context=base.candidate_context,
        saved_preferences=base.saved_preferences,
    )
    investment = DiscoveryPersonalizationService().apply(
        _result("科技投资经理", "unknown"), ranking_input
    )
    assert not any(
        reason.reason_type == "target_role_alignment"
        for reason in investment.personalization_derived.candidate_reasons  # type: ignore[union-attr]
    )


def test_candidate_constraint_supported_gap_and_unknown_are_evidence_based() -> None:
    signal = DiscoveryHardSignal(
        type="experience_years",
        operator=">=",
        value=5,
        display="明确要求 5+ 年经验",
        source_text="5+ years required",
    )
    service = DiscoveryPersonalizationService()
    statuses = []
    for years in (6.0, 1.0, None):
        result = service.apply(
            _result("AI Product Manager", "ai_product", signals=[signal]),
            _ranking_input(years=years),
        )
        statuses.append(result.personalization_derived.candidate_constraint_signals[0].status)  # type: ignore[union-attr]
    assert statuses == ["Supported", "PotentialGap", "Unknown"]

    degree_signal = DiscoveryHardSignal(
        type="degree",
        operator=">=",
        value="bachelor",
        display="明确要求本科及以上学历",
        source_text="Bachelor's degree required",
    )
    degree_statuses = []
    for level in (3, 1, None):
        result = service.apply(
            _result("AI Product Manager", "ai_product", signals=[degree_signal]),
            _ranking_input(education=level),
        )
        degree_statuses.append(
            result.personalization_derived.candidate_constraint_signals[0].status  # type: ignore[union-attr]
        )
    assert degree_statuses == ["Supported", "PotentialGap", "Unknown"]


def test_saved_preferences_never_override_explicit_exclusion_or_requested_growth_role() -> None:
    base = _ranking_input(role_family="growth_product")
    saved_platform = SavedCareerPreferences(
        target_roles=(
            SavedTargetRole("target_role:9", "Platform PM", "primary", "platform_product"),
        ),
        preferred_location="北京",
        target_companies=(),
    )
    ranking_input = PersonalizedRankingInput(
        search_context=_context("growth_product", "Growth Product，不要银行"),
        candidate_context=base.candidate_context,
        saved_preferences=saved_platform,
    )
    growth = DiscoveryPersonalizationService().apply(
        _result("Growth Product Manager", "growth_product"), ranking_input
    )
    platform = DiscoveryPersonalizationService().apply(
        _result("AI Platform Product Manager", "platform_product", "Low"), ranking_input
    )
    banking = _result("Banking AI Product Manager", "ai_product", "Low")
    banking = banking.model_copy(
        update={
            "search_derived": banking.search_derived.model_copy(
                update={"excluded_by_current_search": True, "excluded_matches": ["银行"]}
            )
        }
    )
    banking = DiscoveryPersonalizationService().apply(banking, ranking_input)
    assert growth.personalization_derived.band != "Neutral"  # type: ignore[union-attr]
    assert platform.personalization_derived.band == "Neutral"  # type: ignore[union-attr]
    assert banking.personalization_derived.band == "Neutral"  # type: ignore[union-attr]
    assert DiscoveryService._result_sort_key(growth) < DiscoveryService._result_sort_key(platform)


def test_toggle_removal_restores_public_only_result() -> None:
    service = DiscoveryPersonalizationService()
    original = _result("AI Agent Product Manager", "ai_product")
    personalized = service.apply(original, _ranking_input())
    assert personalized.source_raw == original.source_raw
    assert personalized.normalized == original.normalized
    public = service.remove(personalized)
    assert public.personalization_derived is None
    assert public.search_derived == personalized.search_derived


class _CountingProvider:
    def __init__(self, value=None, *, fail=False):
        self.value = value
        self.fail = fail
        self.calls = 0

    def load(self, _search_context):
        self.calls += 1
        if self.fail:
            raise CandidateDiscoveryContextError("unavailable")
        return self.value


def test_toggle_reranks_in_place_without_source_refetch_and_off_removes_context() -> None:
    db_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    store = InMemoryDiscoverySessionStore()
    context = _context()
    store.create(
        StoredDiscoverySession(
            session=DiscoverySessionRead(
                id="s",
                state="Completed",
                search_context=context,
                source="fixture",
                result_count=1,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            results=[_result("AI Agent Product Manager", "ai_product")],
        )
    )
    provider = _CountingProvider(_ranking_input())
    with Session(db_engine) as db:
        service = DiscoveryService(db, store, candidate_context_provider=provider)
        enabled = service.update_context(
            "s", DiscoveryContextUpdate(personalization_enabled=True)
        )
        personalized = service.result_page(
            "s",
            page=1,
            page_size=25,
            location=None,
            company=None,
            role_family=None,
            relevance=None,
            already_in_my_jobs=None,
            source=None,
            sort="relevance",
        )
        assert enabled.personalization_status == "Ready"
        assert enabled.source_refetch_count == 0
        assert provider.calls == 1
        assert personalized.items[0].personalization_derived is not None
        disabled = service.update_context(
            "s", DiscoveryContextUpdate(personalization_enabled=False)
        )
        assert disabled.personalization_status == "Off"
        assert provider.calls == 1
        assert store.get("s").results[0].personalization_derived is None


def test_personalization_failure_keeps_public_results_available() -> None:
    db_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    store = InMemoryDiscoverySessionStore()
    context = _context()
    store.create(
        StoredDiscoverySession(
            session=DiscoverySessionRead(
                id="s",
                state="Completed",
                search_context=context,
                source="fixture",
                result_count=1,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            results=[_result("AI Product Manager", "ai_product")],
        )
    )
    provider = _CountingProvider(fail=True)
    with Session(db_engine) as db:
        service = DiscoveryService(db, store, candidate_context_provider=provider)
        state = service.update_context(
            "s", DiscoveryContextUpdate(personalization_enabled=True)
        )
        assert state.personalization_status == "Unavailable"
        assert store.get("s").results[0].personalization_derived is None
        assert store.get("s").session.result_count == 1
