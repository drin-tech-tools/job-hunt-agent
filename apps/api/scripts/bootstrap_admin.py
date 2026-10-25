#!/usr/bin/env python3
"""Invite ADMIN_EMAIL and grant admin role for app job-hunt-agent.

Never hardcodes or prints passwords. Supabase sends the invite email; the user
sets their password at /auth/set-password, then enrolls TOTP at /mfa/setup.

Usage (from apps/api):

  uv run python scripts/bootstrap_admin.py

Required env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  ADMIN_EMAIL
"""

from __future__ import annotations

import os
import sys


APP_ID = "job-hunt-agent"


def main() -> int:
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    if not email:
        print("ERROR: ADMIN_EMAIL is required", file=sys.stderr)
        return 1
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 1

    from supabase import create_client

    client = create_client(url, key)

    # Find existing user by email or invite.
    user_id: str | None = None
    try:
        listed = client.auth.admin.list_users()
        users = getattr(listed, "users", None) or []
        for u in users:
            u_email = (getattr(u, "email", None) or "").lower()
            if u_email == email:
                user_id = str(getattr(u, "id", ""))
                break
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed listing users: {exc}", file=sys.stderr)
        return 1

    if not user_id:
        try:
            invited = client.auth.admin.invite_user_by_email(email)
            user = getattr(invited, "user", None)
            user_id = str(getattr(user, "id", "") or "")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: invite failed: {exc}", file=sys.stderr)
            return 1
        if not user_id:
            print("ERROR: invite returned no user id", file=sys.stderr)
            return 1
        print(f"Invited {email} (password not set by this script — check invite email).")
    else:
        print(f"User {email} already exists; granting admin role.")

    try:
        client.table("user_roles").upsert(
            {"user_id": user_id, "app": APP_ID, "role": "admin"},
            on_conflict="user_id,app",
        ).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed writing user_roles: {exc}", file=sys.stderr)
        return 1

    print(f"Granted admin on {APP_ID} for user_id={user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
