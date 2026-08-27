from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import UserProfile
from app.db.session import get_db
from app.main import app
from app.routes.discovery import (
    get_discovery_runner,
    get_discovery_store,
)
from app.schemas.discovery import (
    DiscoveryExplicitConstraints,
    DiscoverySearchContext,
    DiscoverySessionRead,
)
from app.services.discovery_store import InMemoryDiscoverySessionStore, StoredDiscoverySession

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as db:
        yield db


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_search_status_and_invalid_input_contract() -> None:
    store = InMemoryDiscoverySessionStore()
    runner = Mock()
    app.dependency_overrides[get_discovery_store] = lambda: store
    app.dependency_overrides[get_discovery_runner] = lambda: runner
    client = TestClient(app)
    created = client.post(
        "/api/discovery/sessions",
        json={
            "input": "https://jobs.bytedance.com/experienced/position?keywords=AI&location=CT_11",
            "personalization_enabled": False,
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["state"] == "Ready"
    assert payload["search_context"]["explicit_constraints"]["locations"] == ["北京"]
    assert payload["claude_api_calls"] == 0
    started = client.post(f"/api/discovery/sessions/{payload['id']}/search")
    assert started.status_code == 202
    runner.enqueue.assert_called_once()
    assert client.get(f"/api/discovery/sessions/{payload['id']}").status_code == 200

    natural = client.post(
        "/api/discovery/sessions",
        json={"input": "北京 AI 产品经理", "personalization_enabled": False},
    )
    assert natural.status_code == 201
    assert natural.json()["search_context"]["input_kind"] == "natural_language"
    assert natural.json()["claude_api_calls"] == 0
    assert natural.json()["state"] == "Ready"
    assert natural.json()["required_refinement_groups"] == []
    assert natural.json()["optional_refinement_groups"]
    natural_id = natural.json()["id"]
    ecommerce = client.patch(
        f"/api/discovery/sessions/{natural_id}/context",
        json={"selected_tag_ids": ["ecommerce"]},
    )
    assert ecommerce.status_code == 200
    assert ecommerce.json()["search_context"]["refinement_tag_ids"] == ["ecommerce"]
    business_tags = {
        tag["id"]
        for group in ecommerce.json()["optional_refinement_groups"]
        if group["id"] == "business_scenario"
        for tag in group["tags"]
    }
    assert {"ecommerce", "international", "fintech", "enterprise_tob"} <= business_tags
    assert ecommerce.json()["search_context"]["refinement_round"] == 0
    international = client.patch(
        f"/api/discovery/sessions/{natural_id}/context",
        json={"selected_tag_ids": ["ecommerce", "international"]},
    )
    assert international.status_code == 200
    assert international.json()["search_context"]["refinement_tag_ids"] == [
        "ecommerce",
        "international",
    ]
    assert any(
        group["id"] == "business_scenario"
        for group in international.json()["optional_refinement_groups"]
    )
    deselected = client.patch(
        f"/api/discovery/sessions/{natural_id}/context",
        json={"selected_tag_ids": ["international"]},
    )
    assert deselected.status_code == 200
    assert deselected.json()["search_context"]["refinement_tag_ids"] == ["international"]
    assert any(
        tag["id"] == "ecommerce"
        for group in deselected.json()["optional_refinement_groups"]
        for tag in group["tags"]
    )

    # Parent selection offers a child layer without hiding sibling top-level choices.
    refined = client.patch(
        f"/api/discovery/sessions/{natural_id}/context",
        json={"selected_tag_ids": ["ai_agent"], "skip_refinement": False},
    )
    assert refined.status_code == 200
    assert refined.json()["state"] == "Ready"
    assert any(
        group["id"] == "agent_subtype"
        for group in refined.json()["optional_refinement_groups"]
    )
    assert any(
        group["id"] == "business_scenario"
        for group in refined.json()["optional_refinement_groups"]
    )
    assert refined.json()["search_context"]["refinement_round"] == 1
    assert refined.json()["search_context"]["refinement_tag_ids"] == ["ai_agent"]
    removed = client.patch(
        f"/api/discovery/sessions/{natural.json()['id']}/context",
        json={"selected_tag_ids": [], "skip_refinement": False},
    )
    assert removed.status_code == 200
    assert removed.json()["search_context"]["refinement_tag_ids"] == []
    assert "Agent" not in removed.json()["search_context"]["include_terms"]
    second = client.patch(
        f"/api/discovery/sessions/{natural_id}/context",
        json={"selected_tag_ids": ["ai_agent", "agent_platform"], "skip_refinement": False},
    )
    assert second.status_code == 200
    assert second.json()["state"] == "Ready"
    assert second.json()["search_context"]["refinement_round"] == 2

    campus = client.post(
        "/api/discovery/sessions",
        json={"input": "北京 应届 AI 产品经理 字节跳动"},
    )
    assert campus.status_code == 201
    assert campus.json()["selected_source_plans"] == ["bytedance:campus"]
    experienced = client.post(
        "/api/discovery/sessions",
        json={"input": "北京 社招 AI 产品经理 字节跳动"},
    )
    assert experienced.status_code == 201
    assert experienced.json()["selected_source_plans"] == ["bytedance:experienced"]
    unspecified = client.post(
        "/api/discovery/sessions",
        json={"input": "北京 AI 产品经理 字节跳动"},
    )
    assert unspecified.status_code == 201
    assert unspecified.json()["selected_source_plans"] == [
        "bytedance:campus",
        "bytedance:experienced",
    ]

    ambiguous = client.post(
        "/api/discovery/sessions",
        json={"input": "帮我找 AI 工作", "personalization_enabled": False},
    )
    assert ambiguous.status_code == 201
    assert ambiguous.json()["state"] == "NeedsClarification"
    assert ambiguous.json()["required_refinement_groups"][0]["id"] == "job_function"
    blocked = client.patch(
        f"/api/discovery/sessions/{ambiguous.json()['id']}/context",
        json={"selected_tag_ids": [], "skip_refinement": True},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["code"] == "CLARIFICATION_REQUIRED"

    unsupported_site = client.post(
        "/api/discovery/sessions",
        json={"input": "https://careers.example.com/jobs", "personalization_enabled": False},
    )
    assert unsupported_site.status_code == 422
    assert unsupported_site.json()["detail"]["code"] == "UNSUPPORTED_JOB_SOURCE_URL"
    unsupported_xiaomi = client.post(
        "/api/discovery/sessions",
        json={"input": "小米 AI 产品经理 北京", "personalization_enabled": False},
    )
    assert unsupported_xiaomi.status_code == 422
    assert unsupported_xiaomi.json()["detail"] == {
        "code": "NO_SUPPORTED_SOURCES",
        "message": "已理解：北京 · AI Product · 小米。当前暂不支持小米官方招聘源的批量搜索。"
        "你可以粘贴单个岗位链接或 JD。",
    }
    personalized = client.post(
        "/api/discovery/sessions",
        json={
            "input": "https://jobs.bytedance.com/experienced/position",
            "personalization_enabled": True,
        },
    )
    assert personalized.status_code == 201
    assert personalized.json()["search_context"]["personalization_enabled"] is True
    assert personalized.json()["personalization_status"] == "Limited"
    with TestingSession() as db:
        assert db.scalar(select(func.count(UserProfile.id))) == 0
    disabled = client.patch(
        f"/api/discovery/sessions/{personalized.json()['id']}/context",
        json={"personalization_enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["personalization_status"] == "Off"
    assert disabled.json()["source_refetch_count"] == 0


def test_expired_session_returns_410() -> None:
    now = datetime.now(UTC)
    clock = [now]
    store = InMemoryDiscoverySessionStore(clock=lambda: clock[0])
    context = DiscoverySearchContext(
        session_id="expired",
        input_kind="bytedance_search_url",
        raw_input="https://jobs.bytedance.com/experienced/position",
        explicit_constraints=DiscoveryExplicitConstraints(),
        source_hints=["bytedance"],
        created_at=now,
        expires_at=now + timedelta(seconds=1),
    )
    store.create(
        StoredDiscoverySession(
            session=DiscoverySessionRead(
                id="expired",
                state="Ready",
                search_context=context,
                source="bytedance",
                created_at=now,
                expires_at=context.expires_at,
            )
        )
    )
    clock[0] = now + timedelta(seconds=2)
    app.dependency_overrides[get_discovery_store] = lambda: store
    response = TestClient(app).get("/api/discovery/sessions/expired")
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "DISCOVERY_SESSION_EXPIRED"


def test_generalized_dynamic_refinement_updates_typed_context_without_new_call() -> None:
    store = InMemoryDiscoverySessionStore()
    app.dependency_overrides[get_discovery_store] = lambda: store
    client = TestClient(app)

    investment = client.post(
        "/api/discovery/sessions",
        json={"input": "北京 银行 应届 投资", "personalization_enabled": False},
    )
    assert investment.status_code == 201
    payload = investment.json()
    assert payload["state"] == "Ready"
    assert payload["search_context"]["explicit_constraints"]["job_functions"] == [
        "investment"
    ]
    group = payload["optional_refinement_groups"][0]
    assert group["id"] == "investment_subdomain"
    selected = client.patch(
        f"/api/discovery/sessions/{payload['id']}/context",
        json={"selected_tag_ids": ["generalized:investment_subdomain:ibd"]},
    )
    assert selected.status_code == 200
    selected_payload = selected.json()
    assert selected_payload["claude_api_calls"] == payload["claude_api_calls"]
    assert "investment_banking" in selected_payload["search_context"]["include_terms"]

    finance = client.post(
        "/api/discovery/sessions",
        json={"input": "帮我找金融工作", "personalization_enabled": False},
    )
    assert finance.status_code == 201
    finance_payload = finance.json()
    assert finance_payload["state"] == "NeedsClarification"
    assert finance_payload["required_refinement_groups"][0]["id"] == "job_function"
    resolved = client.patch(
        f"/api/discovery/sessions/{finance_payload['id']}/context",
        json={"selected_tag_ids": ["generalized:job_function:investment"]},
    )
    assert resolved.status_code == 200
    assert resolved.json()["state"] == "Ready"
    assert resolved.json()["search_context"]["explicit_constraints"]["job_functions"] == [
        "investment"
    ]
    assert resolved.json()["claude_api_calls"] == finance_payload["claude_api_calls"]
