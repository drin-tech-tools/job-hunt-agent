"""Central RBAC permission matrix for app ``job-hunt-agent``.

Roles
-----
- ``client`` — manage OWN resume, run the agent, OWN tracker items / cover letters,
  view OWN agent runs.
- ``admin`` — everything a client can do for ANY user, plus user management and
  viewing all agent runs / logs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

APP_ID = "job-hunt-agent"

Role = Literal["admin", "client"]


class Permission(StrEnum):
    manage_own_resume = "manage_own_resume"
    manage_any_resume = "manage_any_resume"
    run_agent = "run_agent"
    manage_own_tracker = "manage_own_tracker"
    manage_any_tracker = "manage_any_tracker"
    view_own_agent_runs = "view_own_agent_runs"
    view_any_agent_runs = "view_any_agent_runs"
    manage_users = "manage_users"


# Explicit matrix — single source of truth (mirrored in apps/web/lib/auth/permissions.ts).
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    "client": frozenset(
        {
            Permission.manage_own_resume,
            Permission.run_agent,
            Permission.manage_own_tracker,
            Permission.view_own_agent_runs,
        }
    ),
    "admin": frozenset(
        {
            Permission.manage_own_resume,
            Permission.manage_any_resume,
            Permission.run_agent,
            Permission.manage_own_tracker,
            Permission.manage_any_tracker,
            Permission.view_own_agent_runs,
            Permission.view_any_agent_runs,
            Permission.manage_users,
        }
    ),
}


def can(role: Role | str | None, permission: Permission) -> bool:
    if role not in ROLE_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS[role]  # type: ignore[index]


def require_role(role: Role | str | None, permission: Permission) -> None:
    if not can(role, permission):
        raise PermissionError(f"Role {role!r} lacks permission {permission.value}")


def owns_or_admin(role: Role | str | None, owner_id: str | None, actor_id: str) -> bool:
    """True if actor owns the resource or is admin."""
    if owner_id and owner_id == actor_id:
        return True
    return can(role, Permission.manage_any_resume) or can(role, Permission.manage_any_tracker)
