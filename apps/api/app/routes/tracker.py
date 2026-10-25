"""Application tracker CRUD."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import TrackerCreate, TrackerOut, TrackerUpdate
from app.services.supabase_client import get_db

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.post("", response_model=TrackerOut)
def create_item(body: TrackerCreate) -> TrackerOut:
    row = get_db().create_tracker(body.model_dump())
    return TrackerOut.model_validate(row)


@router.get("", response_model=list[TrackerOut])
def list_items() -> list[TrackerOut]:
    return [TrackerOut.model_validate(r) for r in get_db().list_tracker()]


@router.get("/{item_id}", response_model=TrackerOut)
def get_item(item_id: str) -> TrackerOut:
    row = get_db().get_tracker(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tracker item not found")
    return TrackerOut.model_validate(row)


@router.patch("/{item_id}", response_model=TrackerOut)
def update_item(item_id: str, body: TrackerUpdate) -> TrackerOut:
    row = get_db().update_tracker(item_id, body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Tracker item not found")
    return TrackerOut.model_validate(row)


@router.delete("/{item_id}")
def delete_item(item_id: str) -> dict[str, bool]:
    get_db().delete_tracker(item_id)
    return {"ok": True}
