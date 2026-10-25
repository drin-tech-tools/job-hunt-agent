"""Auth dependency + ownership enforcement tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from tests.conftest import RESUME_TEXT


def test_rejects_without_bearer_when_bypass_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_BYPASS", "0")
    monkeypatch.setenv("AGENT_MOCK", "1")
    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 401
    assert "bearer" in res.json()["detail"].lower() or "Missing" in res.json()["detail"]


def test_rejects_aal1_even_with_bypass(
    client: TestClient, auth_headers_client_aal1: dict[str, str]
) -> None:
    res = client.get("/health", headers=auth_headers_client_aal1)
    assert res.status_code == 401
    assert "AAL2" in res.json()["detail"]


def test_accepts_mock_admin_aal2(
    client: TestClient, auth_headers_admin: dict[str, str]
) -> None:
    res = client.get("/health", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["user_id"] == "mock-admin"


def test_bypass_disabled_in_vercel_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_BYPASS", "1")
    monkeypatch.setenv("AGENT_MOCK", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    res = client.get(
        "/health",
        headers={"Authorization": "Bearer mock.mock-admin.admin.aal2"},
    )
    assert res.status_code == 401


def test_internal_token_alone_is_not_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret-test-token")
    monkeypatch.setenv("AUTH_BYPASS", "0")
    monkeypatch.setenv("AGENT_MOCK", "1")
    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    res = client.get("/health", headers={"X-Internal-Api-Token": "secret-test-token"})
    assert res.status_code == 401


def test_client_cannot_list_admin_users(
    client: TestClient, auth_headers_client: dict[str, str]
) -> None:
    # Without supabase, endpoint returns 503 after permission check — but 403 first.
    res = client.get("/admin/users", headers=auth_headers_client)
    assert res.status_code == 403


def test_client_cannot_see_other_users_tracker(
    client: TestClient,
    auth_headers_admin: dict[str, str],
    auth_headers_client: dict[str, str],
) -> None:
    # Create as admin (owned by mock-admin)
    created = client.post(
        "/tracker",
        headers=auth_headers_admin,
        json={
            "job_id": "j-other",
            "title": "Secret role",
            "company": "OtherCo",
            "apply_url": "https://himalayas.app/jobs/secret",
            "source": "Himalayas",
            "status": "saved",
        },
    )
    assert created.status_code == 200
    item_id = created.json()["id"]
    assert created.json()["user_id"] == "mock-admin"

    # Client list should not include it
    listed = client.get("/tracker", headers=auth_headers_client)
    assert listed.status_code == 200
    assert all(i["id"] != item_id for i in listed.json())

    # Direct get forbidden
    got = client.get(f"/tracker/{item_id}", headers=auth_headers_client)
    assert got.status_code == 403


def test_client_owns_own_resume(
    client: TestClient, auth_headers_client: dict[str, str]
) -> None:
    res = client.post(
        "/resumes",
        headers=auth_headers_client,
        json={"title": "Mine", "content": RESUME_TEXT, "skills": ["Python"]},
    )
    assert res.status_code == 200
    assert res.json()["user_id"] == "user-client-1"

    listed = client.get("/resumes", headers=auth_headers_client)
    assert any(r["id"] == res.json()["id"] for r in listed.json())


def test_admin_sees_all_tracker(
    client: TestClient,
    auth_headers_admin: dict[str, str],
    auth_headers_client: dict[str, str],
) -> None:
    client_item = client.post(
        "/tracker",
        headers=auth_headers_client,
        json={
            "job_id": "j-client",
            "title": "Client role",
            "company": "ClientCo",
            "apply_url": "https://jobicy.com/jobs/1",
            "source": "Jobicy",
        },
    )
    assert client_item.status_code == 200

    listed = client.get("/tracker", headers=auth_headers_admin)
    assert listed.status_code == 200
    assert any(i["id"] == client_item.json()["id"] for i in listed.json())
