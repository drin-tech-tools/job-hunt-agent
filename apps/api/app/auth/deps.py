"""FastAPI dependencies: JWT identity, AAL2, and permission checks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.auth.jwt import (
    decode_jwt_claims_unverified,
    extract_aal,
    load_app_role,
    verify_user_via_supabase,
)
from app.auth.models import CurrentUser
from app.auth.permissions import Permission, can
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

MOCK_BEARER_PREFIX = "mock."


def _auth_bypass_allowed(settings: Settings) -> bool:
    """Test auth bypass only when explicitly enabled and never in production."""
    if not settings.auth_bypass:
        return False
    if settings.is_production:
        return False
    # Require AGENT_MOCK so bypass cannot be enabled against a live agent by mistake.
    if not settings.agent_mock:
        return False
    return True


def _parse_mock_bearer(token: str) -> CurrentUser | None:
    """
    Mock bearer format: ``mock.<user_id>.<role>[.<aal>]``
    Example: ``mock.user-client-1.client.aal2``
    """
    if not token.startswith(MOCK_BEARER_PREFIX):
        return None
    parts = token[len(MOCK_BEARER_PREFIX) :].split(".")
    if len(parts) < 2:
        return None
    user_id, role = parts[0], parts[1]
    aal = parts[2] if len(parts) > 2 else "aal2"
    if role not in ("admin", "client"):
        return None
    return CurrentUser(
        id=user_id,
        email=f"{user_id}@example.test",
        role=role,  # type: ignore[arg-type]
        aal=aal,
        access_token=token,
        is_mock=True,
    )


def _bearer_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """
    Resolve the caller.

    Requires a valid Supabase user access token (Authorization: Bearer).
    INTERNAL_API_TOKEN alone is never enough — reject without a user.
    """
    token = _bearer_from_header(authorization)

    if token and _auth_bypass_allowed(settings):
        mock = _parse_mock_bearer(token)
        if mock is not None:
            if mock.aal != "aal2":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="AAL2 required (TOTP verified)",
                )
            return mock

    if not token:
        # Optional default mock identity when bypass is on and no bearer
        # (eases local health / cucumber default). Prefer explicit bearer.
        if _auth_bypass_allowed(settings):
            return CurrentUser(
                id="mock-admin",
                email="admin@example.test",
                role="admin",
                aal="aal2",
                access_token="mock.mock-admin.admin.aal2",
                is_mock=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer access token",
        )

    if _auth_bypass_allowed(settings) and token.startswith(MOCK_BEARER_PREFIX):
        mock = _parse_mock_bearer(token)
        if mock is None:
            raise HTTPException(status_code=401, detail="Invalid mock token")
        if mock.aal != "aal2":
            raise HTTPException(status_code=401, detail="AAL2 required (TOTP verified)")
        return mock

    try:
        user = verify_user_via_supabase(settings, token)
    except Exception as exc:  # noqa: BLE001
        logger.info("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    user_id = str(user.get("id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user")

    try:
        claims = decode_jwt_claims_unverified(token)
        aal = extract_aal(claims)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid token claims") from exc

    if aal != "aal2":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AAL2 required (TOTP verified)",
        )

    role = load_app_role(settings, user_id)
    if role not in ("admin", "client"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No role assigned for job-hunt-agent",
        )

    return CurrentUser(
        id=user_id,
        email=user.get("email"),
        role=role,  # type: ignore[arg-type]
        aal=aal,
        access_token=token,
        is_mock=False,
    )


async def require_aal2(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Re-check AAL2 (get_current_user already enforces; kept for explicit DI)."""
    if user.aal != "aal2":
        raise HTTPException(status_code=401, detail="AAL2 required (TOTP verified)")
    return user


def require_permission(permission: Permission) -> Callable[..., CurrentUser]:
    async def _dep(user: CurrentUser = Depends(require_aal2)) -> CurrentUser:
        if not can(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return user

    return _dep


def assert_resource_access(
    user: CurrentUser,
    owner_id: str | None,
    *,
    any_perm: Permission,
    own_perm: Permission,
) -> None:
    """Raise 403/404-style denial if the user cannot access a owned resource."""
    if can(user.role, any_perm):
        return
    if owner_id and owner_id == user.id and can(user.role, own_perm):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
