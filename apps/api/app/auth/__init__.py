"""Authentication, identity, and RBAC for the FastAPI service."""

from app.auth.deps import CurrentUser, get_current_user, require_aal2, require_permission
from app.auth.permissions import (
    APP_ID,
    Permission,
    Role,
    can,
    require_role,
)

__all__ = [
    "APP_ID",
    "CurrentUser",
    "Permission",
    "Role",
    "can",
    "get_current_user",
    "require_aal2",
    "require_permission",
    "require_role",
]
