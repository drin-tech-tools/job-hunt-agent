"""Admin invite: normal send, email-delivery fallback to a manual link, other errors."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.routes import admin_users


class _FakeTable:
    def __init__(self, store: list[dict[str, Any]]) -> None:
        self._store = store

    def upsert(self, row: dict[str, Any], **_: Any) -> _FakeTable:
        self._store.append(row)
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._store)


class _FakeAdmin:
    def __init__(self, invite_error: Exception | None, link_error: Exception | None) -> None:
        self._invite_error = invite_error
        self._link_error = link_error

    def invite_user_by_email(self, email: str, options: dict[str, Any] | None = None):
        if self._invite_error:
            raise self._invite_error
        return SimpleNamespace(user=SimpleNamespace(id="user-1", email=email))

    def generate_link(self, params: dict[str, Any]):
        if self._link_error:
            raise self._link_error
        assert params["type"] == "invite"
        return SimpleNamespace(
            user=SimpleNamespace(id="user-2", email=params["email"]),
            properties=SimpleNamespace(action_link="https://example.test/verify?token=abc"),
        )


def _install_fake(
    monkeypatch: pytest.MonkeyPatch,
    invite_error: Exception | None = None,
    link_error: Exception | None = None,
) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    fake = SimpleNamespace(
        auth=SimpleNamespace(admin=_FakeAdmin(invite_error, link_error)),
        table=lambda _name: _FakeTable(roles),
    )
    monkeypatch.setattr(admin_users, "_admin_client", lambda: fake)
    return roles


def _invite(client: TestClient, headers: dict[str, str]):
    return client.post(
        "/admin/users/invite",
        json={"email": "new@example.test", "role": "client"},
        headers=headers,
    )


def test_invite_sent_has_no_link(
    client: TestClient, auth_headers_admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    roles = _install_fake(monkeypatch)
    res = _invite(client, auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["invite_link"] is None
    assert roles[0]["user_id"] == "user-1"


def test_email_failure_falls_back_to_manual_link(
    client: TestClient, auth_headers_admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    roles = _install_fake(monkeypatch, invite_error=Exception("Error sending invite email"))
    res = _invite(client, auth_headers_admin)
    assert res.status_code == 200
    body = res.json()
    assert body["invite_link"] == "https://example.test/verify?token=abc"
    assert body["id"] == "user-2"
    assert roles[0] == {"user_id": "user-2", "app": "job-hunt-agent", "role": "client"}


def test_email_and_link_failure_returns_smtp_hint(
    client: TestClient, auth_headers_admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake(
        monkeypatch,
        invite_error=Exception("Error sending invite email"),
        link_error=Exception("boom"),
    )
    res = _invite(client, auth_headers_admin)
    assert res.status_code == 502
    assert "SMTP" in res.json()["detail"]


def test_other_invite_errors_are_not_masked(
    client: TestClient, auth_headers_admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake(monkeypatch, invite_error=Exception("User already registered"))
    res = _invite(client, auth_headers_admin)
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"]


def test_client_role_cannot_invite(
    client: TestClient, auth_headers_client: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake(monkeypatch)
    assert _invite(client, auth_headers_client).status_code == 403
