"""Admin-only user management (invite, list, role, disable, reset MFA)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import require_permission
from app.auth.models import CurrentUser
from app.auth.permissions import APP_ID, Permission
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])

RoleLiteral = Literal["admin", "client"]


class InviteRequest(BaseModel):
    email: str = Field(..., min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: RoleLiteral = "client"


class RoleUpdateRequest(BaseModel):
    role: RoleLiteral


class UserOut(BaseModel):
    id: str
    email: str | None = None
    role: RoleLiteral | None = None
    banned: bool = False
    factors: int = 0


def _admin_client():  # type: ignore[no-untyped-def]
    settings = get_settings()
    if not settings.supabase_configured:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@router.get("", response_model=list[UserOut])
def list_users(
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> list[UserOut]:
    client = _admin_client()
    # List auth users (paginated — first page is enough for small invite-only apps).
    try:
        listed = client.auth.admin.list_users()
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_users failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    users = getattr(listed, "users", None) or listed or []
    role_rows = (
        client.table("user_roles")
        .select("user_id, role")
        .eq("app", APP_ID)
        .execute()
        .data
        or []
    )
    roles = {r["user_id"]: r["role"] for r in role_rows}

    out: list[UserOut] = []
    for u in users:
        uid = str(getattr(u, "id", None) or u.get("id") if isinstance(u, dict) else "")
        email = getattr(u, "email", None) if not isinstance(u, dict) else u.get("email")
        banned_until = (
            getattr(u, "banned_until", None)
            if not isinstance(u, dict)
            else u.get("banned_until")
        )
        factors = 0
        try:
            fl = client.auth.admin.mfa.list_factors(uid)
            totp = getattr(fl, "totp", None) or []
            factors = len(totp)
        except Exception:  # noqa: BLE001
            factors = 0
        out.append(
            UserOut(
                id=uid,
                email=email,
                role=roles.get(uid),
                banned=bool(banned_until),
                factors=factors,
            )
        )
    return out


@router.post("/invite", response_model=UserOut)
def invite_user(
    body: InviteRequest,
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> UserOut:
    client = _admin_client()
    try:
        invited = client.auth.admin.invite_user_by_email(body.email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invite failed: {exc}") from exc

    user = getattr(invited, "user", None) or invited
    uid = str(getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else ""))
    if not uid:
        raise HTTPException(status_code=502, detail="Invite returned no user id")

    client.table("user_roles").upsert(
        {"user_id": uid, "app": APP_ID, "role": body.role},
        on_conflict="user_id,app",
    ).execute()

    return UserOut(id=uid, email=body.email, role=body.role, banned=False, factors=0)


@router.patch("/{user_id}/role", response_model=UserOut)
def set_role(
    user_id: str,
    body: RoleUpdateRequest,
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> UserOut:
    client = _admin_client()
    client.table("user_roles").upsert(
        {"user_id": user_id, "app": APP_ID, "role": body.role},
        on_conflict="user_id,app",
    ).execute()
    return UserOut(id=user_id, role=body.role)


@router.post("/{user_id}/disable")
def disable_user(
    user_id: str,
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> dict[str, bool]:
    client = _admin_client()
    try:
        # Ban for a long period (Supabase admin update_user_by_id ban_duration).
        client.auth.admin.update_user_by_id(user_id, {"ban_duration": "876600h"})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.delete("/{user_id}")
def remove_user(
    user_id: str,
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> dict[str, bool]:
    client = _admin_client()
    try:
        client.auth.admin.delete_user(user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    client.table("user_roles").delete().eq("user_id", user_id).eq("app", APP_ID).execute()
    return {"ok": True}


@router.post("/{user_id}/reset-mfa")
def reset_mfa(
    user_id: str,
    _admin: CurrentUser = Depends(require_permission(Permission.manage_users)),
) -> dict[str, Any]:
    client = _admin_client()
    removed = 0
    try:
        factors = client.auth.admin.mfa.list_factors(user_id)
        for factor in getattr(factors, "totp", None) or []:
            fid = getattr(factor, "id", None) or factor.get("id")
            if fid:
                client.auth.admin.mfa.delete_factor(user_id=user_id, id=fid)
                removed += 1
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "removed": removed}
