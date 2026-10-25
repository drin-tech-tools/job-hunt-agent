"""Health check."""

from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.services.supabase_client import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    db = get_db()
    return {
        "status": "ok",
        "version": __version__,
        "gemini_configured": bool(settings.gemini_api_key),
        "supabase": "memory" if db.using_memory else "connected",
        "jsearch_enabled": settings.jsearch_enabled,
    }
