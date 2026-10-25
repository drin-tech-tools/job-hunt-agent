"""Auth identity models."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth.permissions import Role


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Authenticated caller after JWT + AAL2 + role resolution."""

    id: str
    email: str | None
    role: Role
    aal: str
    access_token: str
    is_mock: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
