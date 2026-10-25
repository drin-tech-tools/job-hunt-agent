"""Supabase client helpers with graceful in-memory fallback for local/tests."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# In-memory stores used when Supabase is not configured (local/tests).
_memory: dict[str, dict[str, Any]] = {
    "resumes": {},
    "jobs_cache": {},
    "tracker": {},
    "agent_runs": {},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SupabaseService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.supabase_configured:
            try:
                from supabase import create_client

                self._client = create_client(
                    self.settings.supabase_url,
                    self.settings.supabase_service_role_key,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Supabase client init failed, using memory store: %s", exc)
                self._client = None

    @property
    def using_memory(self) -> bool:
        return self._client is None

    # ---- resumes ----
    def create_resume(
        self,
        title: str,
        content: str,
        skills: list[str],
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "skills": skills,
            "user_id": user_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        if self._client:
            res = self._client.table("resumes").insert(row).execute()
            return res.data[0]
        _memory["resumes"][row["id"]] = row
        return row

    def get_resume(self, resume_id: str) -> dict[str, Any] | None:
        if self._client:
            res = self._client.table("resumes").select("*").eq("id", resume_id).limit(1).execute()
            return res.data[0] if res.data else None
        return _memory["resumes"].get(resume_id)

    def list_resumes(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        """If ``user_id`` is set, filter to that owner; ``None`` means all (admin)."""
        if self._client:
            q = self._client.table("resumes").select("*")
            if user_id is not None:
                q = q.eq("user_id", user_id)
            res = q.order("created_at", desc=True).execute()
            return list(res.data or [])
        rows = list(_memory["resumes"].values())
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        return sorted(
            rows,
            key=lambda r: r.get("created_at", ""),
            reverse=True,
        )

    def delete_resume(self, resume_id: str) -> bool:
        if self._client:
            self._client.table("resumes").delete().eq("id", resume_id).execute()
            return True
        return _memory["resumes"].pop(resume_id, None) is not None

    # ---- jobs cache ----
    def get_jobs_cache(self, cache_key: str, ttl_s: int) -> list[dict[str, Any]] | None:
        if self._client:
            res = (
                self._client.table("jobs_cache")
                .select("*")
                .eq("cache_key", cache_key)
                .limit(1)
                .execute()
            )
            if not res.data:
                return None
            row = res.data[0]
            created = row.get("created_at")
            try:
                ts = datetime.fromisoformat(str(created).replace("Z", "+00:00")).timestamp()
            except Exception:  # noqa: BLE001
                return None
            if time.time() - ts > ttl_s:
                return None
            return row.get("jobs") or []

        row = _memory["jobs_cache"].get(cache_key)
        if not row:
            return None
        if time.time() - row["ts"] > ttl_s:
            return None
        return row["jobs"]

    def set_jobs_cache(self, cache_key: str, jobs: list[dict[str, Any]]) -> None:
        payload = {
            "cache_key": cache_key,
            "jobs": jobs,
            "created_at": _now_iso(),
        }
        if self._client:
            self._client.table("jobs_cache").upsert(payload, on_conflict="cache_key").execute()
            return
        _memory["jobs_cache"][cache_key] = {"jobs": jobs, "ts": time.time()}

    # ---- tracker ----
    def create_tracker(self, data: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            **data,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        if self._client:
            res = self._client.table("tracker").insert(row).execute()
            return res.data[0]
        _memory["tracker"][row["id"]] = row
        return row

    def list_tracker(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        if self._client:
            q = self._client.table("tracker").select("*")
            if user_id is not None:
                q = q.eq("user_id", user_id)
            res = q.order("updated_at", desc=True).execute()
            return list(res.data or [])
        rows = list(_memory["tracker"].values())
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        return sorted(
            rows,
            key=lambda r: r.get("updated_at", ""),
            reverse=True,
        )

    def get_tracker(self, item_id: str) -> dict[str, Any] | None:
        if self._client:
            res = self._client.table("tracker").select("*").eq("id", item_id).limit(1).execute()
            return res.data[0] if res.data else None
        return _memory["tracker"].get(item_id)

    def update_tracker(self, item_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        patch = {k: v for k, v in patch.items() if v is not None}
        patch["updated_at"] = _now_iso()
        if self._client:
            res = self._client.table("tracker").update(patch).eq("id", item_id).execute()
            return res.data[0] if res.data else None
        row = _memory["tracker"].get(item_id)
        if not row:
            return None
        row.update(patch)
        return row

    def delete_tracker(self, item_id: str) -> bool:
        if self._client:
            self._client.table("tracker").delete().eq("id", item_id).execute()
            return True
        return _memory["tracker"].pop(item_id, None) is not None

    # ---- agent runs ----
    def create_agent_run(self, data: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            **data,
            "created_at": _now_iso(),
        }
        if self._client:
            res = self._client.table("agent_runs").insert(row).execute()
            return res.data[0]
        _memory["agent_runs"][row["id"]] = row
        return row

    def update_agent_run(self, run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if self._client:
            res = self._client.table("agent_runs").update(patch).eq("id", run_id).execute()
            return res.data[0] if res.data else None
        row = _memory["agent_runs"].get(run_id)
        if not row:
            return None
        row.update(patch)
        return row


_service: SupabaseService | None = None


def get_db() -> SupabaseService:
    global _service
    if _service is None:
        _service = SupabaseService()
    return _service


def reset_db_for_tests() -> None:
    """Clear memory store and cached service (tests only)."""
    global _service
    _service = None
    for key in _memory:
        _memory[key] = {}
