"""Liveness/readiness. Requires AAL2 user (AUTH_BYPASS synthesizes mock admin in tests)."""

from fastapi import APIRouter, Depends

from app import __version__
from app.auth.deps import require_aal2
from app.auth.models import CurrentUser
from app.config import get_settings
from app.services.supabase_client import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(user: CurrentUser = Depends(require_aal2)) -> dict:
    settings = get_settings()
    db = get_db()
    return {
        "status": "ok",
        "version": __version__,
        "gemini_configured": bool(settings.gemini_api_key),
        "supabase": "memory" if db.using_memory else "connected",
        "jsearch_enabled": settings.jsearch_enabled,
        "auth_bypass": bool(settings.auth_bypass and not settings.is_production),
        "user_id": user.id,
    }
