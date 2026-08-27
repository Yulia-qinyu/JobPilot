import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.schemas.analysis import Project, ResumeProfile, WorkExperience
from app.schemas.profile import TargetRoleUpdate
from app.services.profile_service import ProfileLimitError, ProfileService


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_profile_targets_location_and_limit_are_persisted(db: Session) -> None:
    service = ProfileService(db)
    service.update_location("Sydney, Australia")
    for name in ["Atlassian", "Canva", "Google", "Microsoft", "Airwallex"]:
        service.add_company(name)

    persisted = ProfileService(db).get_profile()

    assert persisted.preferred_location == "Sydney, Australia"
    assert [item.name for item in persisted.target_companies] == [
        "Atlassian",
        "Canva",
        "Google",
        "Microsoft",
        "Airwallex",
    ]
    with pytest.raises(ProfileLimitError, match="up to 5"):
        service.add_company("Anthropic")


def test_target_role_auto_classification_override_and_clear(db: Session) -> None:
    service = ProfileService(db)

    profile = service.add_role("AI 产品经理", "secondary")
    role = profile.target_roles[0]
    assert role.priority == "secondary"
    assert role.auto_role_family == "ai_product"
    assert role.role_family_override is None
    assert role.effective_role_family == "ai_product"

    profile = service.update_role(role.id, TargetRoleUpdate(name="数据产品经理"))
    role = profile.target_roles[0]
    assert role.auto_role_family == "data_product"
    assert role.effective_role_family == "data_product"
    assert role.priority == "secondary"

    profile = service.update_role(
        role.id, TargetRoleUpdate(role_family_override="strategy_product")
    )
    role = profile.target_roles[0]
    assert role.role_family_override == "strategy_product"
    assert role.effective_role_family == "strategy_product"

    profile = service.update_role(role.id, TargetRoleUpdate(name="FinTech Product Manager"))
    role = profile.target_roles[0]
    assert role.auto_role_family == "fintech_product"
    assert role.effective_role_family == "strategy_product"

    profile = service.update_role(role.id, TargetRoleUpdate(role_family_override=None))
    role = profile.target_roles[0]
    assert role.role_family_override is None
    assert role.effective_role_family == "fintech_product"

    profile = service.delete_role(role.id)
    assert profile.target_roles == []


def test_resume_creates_only_resume_derived_experience_facts(db: Session) -> None:
    parsed = ResumeProfile(
        work_experience=[
            WorkExperience(
                company="Acme",
                title="Product Manager",
                period="2024–2026",
                highlights=["Launched an AI workflow used by 200 customers."],
            )
        ],
        projects=[Project(name="JobPilot", description="Built a resume matching prototype.")],
    )

    profile = ProfileService(db).replace_resume("master.docx", "resume text", parsed)

    assert profile.resume is not None
    assert profile.resume.original_filename == "master.docx"
    assert len(profile.experiences) == 2
    assert profile.experiences[0].facts[0].source_type == "resume"
    assert profile.experiences[0].facts[0].confirmed is False
    assert profile.experiences[0].facts[0].text == "Launched an AI workflow used by 200 customers."


def test_manual_fact_can_be_added_edited_confirmed_and_deleted(db: Session) -> None:
    service = ProfileService(db)
    profile = service.replace_resume(
        "master.docx",
        "resume text",
        ResumeProfile(work_experience=[WorkExperience(company="Acme", title="PM", highlights=[])]),
    )
    experience_id = profile.experiences[0].id

    profile = service.add_fact(experience_id, "Interviewed 12 enterprise users.", False)
    fact = profile.experiences[0].facts[0]
    assert fact.source_type == "manual"

    profile = service.update_fact(fact.id, text="Interviewed 15 enterprise users.", confirmed=True)
    updated = profile.experiences[0].facts[0]
    assert updated.text == "Interviewed 15 enterprise users."
    assert updated.confirmed is True

    profile = service.delete_fact(fact.id)
    assert profile.experiences[0].facts == []


def test_replacing_resume_preserves_manual_facts_but_refreshes_resume_facts(db: Session) -> None:
    service = ProfileService(db)
    first = service.replace_resume(
        "old.docx",
        "old",
        ResumeProfile(
            work_experience=[
                WorkExperience(company="Acme", title="PM", highlights=["Old resume fact."])
            ]
        ),
    )
    old_experience_id = first.experiences[0].id
    service.add_fact(old_experience_id, "Manual ground-truth fact.", True)

    replaced = service.replace_resume(
        "new.docx",
        "new",
        ResumeProfile(
            work_experience=[
                WorkExperience(company="Beta", title="Senior PM", highlights=["New resume fact."])
            ]
        ),
    )

    facts = [fact for experience in replaced.experiences for fact in experience.facts]
    assert {fact.text for fact in facts} == {"Manual ground-truth fact.", "New resume fact."}
    assert next(fact for fact in facts if fact.text.startswith("Manual")).confirmed is True
