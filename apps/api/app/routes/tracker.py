"""Application tracker CRUD with ownership + RBAC."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import assert_resource_access, require_aal2, require_permission
from app.auth.models import CurrentUser
from app.auth.permissions import Permission, can
from app.models.schemas import TrackerCreate, TrackerOut, TrackerUpdate
from app.services.supabase_client import get_db

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.post("", response_model=TrackerOut)
def create_item(
    body: TrackerCreate,
    user: CurrentUser = Depends(require_permission(Permission.manage_own_tracker)),
) -> TrackerOut:
    payload = body.model_dump()
    payload["user_id"] = user.id
    row = get_db().create_tracker(payload)
    return TrackerOut.model_validate(row)


@router.get("", response_model=list[TrackerOut])
def list_items(
    user: CurrentUser = Depends(require_aal2),
) -> list[TrackerOut]:
    if not can(user.role, Permission.manage_own_tracker):
        raise HTTPException(status_code=403, detail="Forbidden")
    owner = None if can(user.role, Permission.manage_any_tracker) else user.id
    return [TrackerOut.model_validate(r) for r in get_db().list_tracker(user_id=owner)]


@router.get("/{item_id}", response_model=TrackerOut)
def get_item(
    item_id: str,
    user: CurrentUser = Depends(require_aal2),
) -> TrackerOut:
    row = get_db().get_tracker(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tracker item not found")
    assert_resource_access(
        user,
        row.get("user_id"),
        any_perm=Permission.manage_any_tracker,
        own_perm=Permission.manage_own_tracker,
    )
    return TrackerOut.model_validate(row)


@router.patch("/{item_id}", response_model=TrackerOut)
def update_item(
    item_id: str,
    body: TrackerUpdate,
    user: CurrentUser = Depends(require_aal2),
) -> TrackerOut:
    existing = get_db().get_tracker(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Tracker item not found")
    assert_resource_access(
        user,
        existing.get("user_id"),
        any_perm=Permission.manage_any_tracker,
        own_perm=Permission.manage_own_tracker,
    )
    row = get_db().update_tracker(item_id, body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Tracker item not found")
    return TrackerOut.model_validate(row)


@router.delete("/{item_id}")
def delete_item(
    item_id: str,
    user: CurrentUser = Depends(require_aal2),
) -> dict[str, bool]:
    existing = get_db().get_tracker(item_id)
    if existing:
        assert_resource_access(
            user,
            existing.get("user_id"),
            any_perm=Permission.manage_any_tracker,
            own_perm=Permission.manage_own_tracker,
        )
        get_db().delete_tracker(item_id)
    return {"ok": True}
