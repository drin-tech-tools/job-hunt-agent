"""Resume CRUD."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import ResumeCreate, ResumeOut
from app.services.supabase_client import get_db

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeOut)
def create_resume(body: ResumeCreate) -> ResumeOut:
    row = get_db().create_resume(body.title, body.content, body.skills)
    return ResumeOut.model_validate(row)


@router.get("", response_model=list[ResumeOut])
def list_resumes() -> list[ResumeOut]:
    return [ResumeOut.model_validate(r) for r in get_db().list_resumes()]


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: str) -> ResumeOut:
    row = get_db().get_resume(resume_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeOut.model_validate(row)


@router.delete("/{resume_id}")
def delete_resume(resume_id: str) -> dict[str, bool]:
    ok = get_db().delete_resume(resume_id)
    if not ok:
        # Memory store returns False when missing; Supabase delete is idempotent
        pass
    return {"ok": True}
