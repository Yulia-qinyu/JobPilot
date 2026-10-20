from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Job, JobNote
from app.repositories.profile_repository import DEFAULT_PROFILE_ID, ProfileRepository
from app.services.job_note_service import JobNoteError, JobNoteService

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def make_job(db: Session) -> Job:
    ProfileRepository(db).ensure_default_profile()
    job = Job(
        user_profile_id=DEFAULT_PROFILE_ID,
        company="京东",
        role="产品经理",
        original_jd="",
        structured_jd={},
        status="Interested",
        source_content_hash="n" * 64,
    )
    db.add(job)
    db.commit()
    return job


def test_human_note_lifecycle_and_agent_notes_are_read_only() -> None:
    with TestingSession() as db:
        job = make_job(db)
        original_updated_at = job.updated_at
        service = JobNoteService(db)
        human = service.create_human_note(job.id, "  HR 说周一电话联系  ")
        db.commit()
        assert human.content == "HR 说周一电话联系"
        assert human.author_type == "human"
        assert job.updated_at >= original_updated_at

        service.update_human_note(job.id, human.id, "周二电话联系")
        agent = JobNote(
            user_profile_id=DEFAULT_PROFILE_ID,
            job_id=job.id,
            content="历史兼容备注",
            author_type="agent",
            metadata_json={"source": "legacy_import"},
            dedupe_key="legacy:1",
        )
        db.add(agent)
        db.commit()
        with pytest.raises(JobNoteError, match="read-only"):
            service.update_human_note(job.id, agent.id, "不能修改")
        db.rollback()

        notes = service.list_notes(job.id)
        assert [item.content for item in notes] == [
            "历史兼容备注",
            "周二电话联系",
        ]
        service.delete_human_note(job.id, human.id)
        db.commit()
        assert len(service.list_notes(job.id)) == 1

def test_latest_notes_are_loaded_in_one_bounded_query_shape() -> None:
    with TestingSession() as db:
        first_job = make_job(db)
        second_job = Job(
            user_profile_id=DEFAULT_PROFILE_ID,
            company="腾讯",
            role="数据产品经理",
            original_jd="",
            structured_jd={},
            status="Interested",
            source_content_hash="m" * 64,
        )
        db.add(second_job)
        db.commit()
        service = JobNoteService(db)
        service.create_human_note(first_job.id, "旧备注")
        newest = service.create_human_note(first_job.id, "新备注")
        service.create_human_note(second_job.id, "另一岗位")
        newest.created_at = datetime.now(UTC)
        db.commit()

        latest = service.latest_for_jobs([first_job.id, second_job.id])
        assert latest[first_job.id].content == "新备注"
        assert latest[second_job.id].content == "另一岗位"
