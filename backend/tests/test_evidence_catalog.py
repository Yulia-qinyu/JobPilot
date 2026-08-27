from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.repositories.profile_repository import ProfileRepository
from app.schemas.analysis import ResumeProfile, WorkExperience
from app.services.evidence_catalog import EvidenceCatalogBuilder
from app.services.hard_requirements import validate_hard_requirement
from app.services.profile_service import ProfileService
from app.services.requirement_catalog import ScoredRequirement


def test_only_resume_extracted_and_confirmed_manual_facts_are_eligible() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        profile = ProfileService(db).replace_resume(
            "master.docx",
            "private resume text",
            ResumeProfile(
                skills=["SQL"],
                work_experience=[
                    WorkExperience(company="Acme", title="PM", highlights=["Shipped AI workflow."])
                ],
            ),
        )
        experience_id = profile.experiences[0].id
        profile = ProfileService(db).add_fact(experience_id, "Unconfirmed manual claim.", False)
        unconfirmed_id = next(
            fact.id for fact in profile.experiences[0].facts if fact.source_type == "manual"
        )
        profile = ProfileService(db).add_fact(experience_id, "Confirmed customer research.", True)
        confirmed_id = max(fact.id for fact in profile.experiences[0].facts)

        catalog = EvidenceCatalogBuilder().build(ProfileRepository(db).get_full_profile())

    assert {item.source_type for item in catalog.sources} == {
        "resume_extracted",
        "manual_confirmed",
    }
    assert str(confirmed_id) in {item.source_id for item in catalog.sources}
    assert str(unconfirmed_id) not in {item.source_id for item in catalog.sources}
    assert "private resume text" not in " ".join(item.text for item in catalog.sources)


def test_hard_requirement_validation_is_conservative_and_categorized() -> None:
    required_years = ScoredRequirement(
        "r1", "At least 5 years of product experience", "Required", "high", "key_requirement"
    )
    preferred_degree = ScoredRequirement("r2", "MBA preferred", "A plus", "low", "key_requirement")
    work_eligibility = ScoredRequirement(
        "r3", "Must have US work authorization", "Required", "high", "key_requirement"
    )
    graduation_eligibility = ScoredRequirement(
        "r4", "2027届本科及以上学历", "校园招聘要求", "high", "key_requirement"
    )

    assert validate_hard_requirement(required_years, True) == (True, "experience")
    assert validate_hard_requirement(preferred_degree, True) == (False, "none")
    assert validate_hard_requirement(work_eligibility, True) == (True, "eligibility")
    assert validate_hard_requirement(graduation_eligibility, True) == (True, "eligibility")
