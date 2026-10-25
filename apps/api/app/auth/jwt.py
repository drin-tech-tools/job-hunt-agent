"""Supabase JWT verification (get_user / JWKS) and AAL claim extraction."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# Cache JWKS briefly in-process (pytest / cold starts stay simple).
_jwks_cache: dict[str, Any] | None = None


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def decode_jwt_claims_unverified(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (use only after get_user / JWKS)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")
    payload = _b64url_decode(parts[1])
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JWT payload must be an object")
    return data


def extract_aal(claims: dict[str, Any]) -> str:
    """Return authenticator assurance level from JWT claims (default aal1)."""
    aal = claims.get("aal") or claims.get("amr")
    if isinstance(aal, str) and aal.startswith("aal"):
        return aal
    # amr may be a list of method objects; prefer explicit aal claim
    if isinstance(claims.get("aal"), str):
        return str(claims["aal"])
    return "aal1"


async def fetch_jwks(settings: Settings) -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required for JWKS verification")
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url)
        res.raise_for_status()
        _jwks_cache = res.json()
        return _jwks_cache


def clear_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None


def verify_user_via_supabase(settings: Settings, access_token: str) -> dict[str, Any]:
    """
    Validate the access token with Supabase Auth and return the user dict.

    Uses the service-role client + ``auth.get_user(jwt)`` which validates the
    token server-side (works for both legacy HS256 and new asymmetric JWKS keys).
    """
    if not settings.supabase_configured:
        raise RuntimeError("Supabase is not configured")

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    res = client.auth.get_user(access_token)
    user = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
    if user is None:
        raise ValueError("Invalid or expired access token")
    # supabase-py returns a User object
    if hasattr(user, "model_dump"):
        return user.model_dump()
    if hasattr(user, "dict"):
        return user.dict()  # type: ignore[no-any-return]
    if isinstance(user, dict):
        return user
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
    }


def load_app_role(settings: Settings, user_id: str) -> str | None:
    """Load role for ``job-hunt-agent`` from ``public.user_roles``."""
    from app.auth.permissions import APP_ID

    if not settings.supabase_configured:
        return None

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    res = (
        client.table("user_roles")
        .select("role")
        .eq("user_id", user_id)
        .eq("app", APP_ID)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    return rows[0].get("role")
