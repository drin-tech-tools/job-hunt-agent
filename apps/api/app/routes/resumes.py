"""Resume CRUD with ownership + RBAC."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import assert_resource_access, require_aal2, require_permission
from app.auth.models import CurrentUser
from app.auth.permissions import Permission, can
from app.models.schemas import ResumeCreate, ResumeOut
from app.services.supabase_client import get_db

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeOut)
def create_resume(
    body: ResumeCreate,
    user: CurrentUser = Depends(require_permission(Permission.manage_own_resume)),
) -> ResumeOut:
    row = get_db().create_resume(body.title, body.content, body.skills, user_id=user.id)
    return ResumeOut.model_validate(row)


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    user: CurrentUser = Depends(require_aal2),
) -> list[ResumeOut]:
    if not can(user.role, Permission.manage_own_resume):
        raise HTTPException(status_code=403, detail="Forbidden")
    owner = None if can(user.role, Permission.manage_any_resume) else user.id
    return [ResumeOut.model_validate(r) for r in get_db().list_resumes(user_id=owner)]


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(
    resume_id: str,
    user: CurrentUser = Depends(require_aal2),
) -> ResumeOut:
    row = get_db().get_resume(resume_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    assert_resource_access(
        user,
        row.get("user_id"),
        any_perm=Permission.manage_any_resume,
        own_perm=Permission.manage_own_resume,
    )
    return ResumeOut.model_validate(row)


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: str,
    user: CurrentUser = Depends(require_aal2),
) -> dict[str, bool]:
    row = get_db().get_resume(resume_id)
    if row:
        assert_resource_access(
            user,
            row.get("user_id"),
            any_perm=Permission.manage_any_resume,
            own_perm=Permission.manage_own_resume,
        )
        get_db().delete_resume(resume_id)
    return {"ok": True}
