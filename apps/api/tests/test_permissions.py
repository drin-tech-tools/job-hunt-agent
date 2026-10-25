"""Permission matrix unit tests."""

from __future__ import annotations

import pytest

from app.auth.permissions import ROLE_PERMISSIONS, Permission, can


@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        ("client", Permission.manage_own_resume, True),
        ("client", Permission.manage_any_resume, False),
        ("client", Permission.run_agent, True),
        ("client", Permission.manage_own_tracker, True),
        ("client", Permission.manage_any_tracker, False),
        ("client", Permission.view_own_agent_runs, True),
        ("client", Permission.view_any_agent_runs, False),
        ("client", Permission.manage_users, False),
        ("admin", Permission.manage_own_resume, True),
        ("admin", Permission.manage_any_resume, True),
        ("admin", Permission.run_agent, True),
        ("admin", Permission.manage_own_tracker, True),
        ("admin", Permission.manage_any_tracker, True),
        ("admin", Permission.view_own_agent_runs, True),
        ("admin", Permission.view_any_agent_runs, True),
        ("admin", Permission.manage_users, True),
        (None, Permission.run_agent, False),
        ("unknown", Permission.run_agent, False),
    ],
)
def test_permission_matrix(role: str | None, permission: Permission, expected: bool) -> None:
    assert can(role, permission) is expected


def test_admin_is_superset_of_client() -> None:
    assert ROLE_PERMISSIONS["client"] <= ROLE_PERMISSIONS["admin"]
