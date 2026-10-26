#!/usr/bin/env python3
"""Invite ADMIN_EMAIL and grant admin role for app job-hunt-agent.

Never hardcodes or prints passwords. Supabase sends the invite (or recovery)
email; the user sets their password at /auth/set-password, then enrolls TOTP.

- New user: invite email with redirect_to → /auth/callback?next=/auth/set-password
- Existing user (invite consumed): recovery email to the same redirect_to

Usage (from apps/api):

  uv run python scripts/bootstrap_admin.py

Required env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  ADMIN_EMAIL

Optional:
  SITE_URL / NEXT_PUBLIC_SITE_URL — defaults to https://job-hunt-agent-eta.vercel.app
"""

from __future__ import annotations

import os
import sys

import httpx

APP_ID = "job-hunt-agent"
DEFAULT_SITE_URL = "https://job-hunt-agent-eta.vercel.app"


def _site_url() -> str:
    raw = (
        os.environ.get("SITE_URL")
        or os.environ.get("NEXT_PUBLIC_SITE_URL")
        or DEFAULT_SITE_URL
    )
    return raw.strip().rstrip("/")


def _redirect_to() -> str:
    return f"{_site_url()}/auth/callback?next=/auth/set-password"


def _send_recovery(base: str, service_key: str, email: str, redirect_to: str) -> None:
    """Send a recovery email via Auth Admin HTTP (works when invite was already consumed)."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        res = client.post(
            f"{base}/auth/v1/recover",
            headers=headers,
            json={"email": email, "redirect_to": redirect_to},
        )
        if res.is_success:
            return
        # Some GoTrue builds expect camelCase redirectTo.
        retry = client.post(
            f"{base}/auth/v1/recover",
            headers=headers,
            json={"email": email, "redirectTo": redirect_to},
        )
        if not retry.is_success:
            detail = retry.text or res.text or f"HTTP {res.status_code}"
            raise RuntimeError(f"Recovery failed: {detail}")


def main() -> int:
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    if not email:
        print("ERROR: ADMIN_EMAIL is required", file=sys.stderr)
        return 1
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 1

    redirect_to = _redirect_to()
    print(f"Bootstrapping {email} as admin for {APP_ID}…")
    print(f"redirectTo: {redirect_to}")

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

    emailed: str
    if not user_id:
        try:
            invited = client.auth.admin.invite_user_by_email(
                email,
                options={"redirect_to": redirect_to},
            )
            user = getattr(invited, "user", None)
            user_id = str(getattr(user, "id", "") or "")
            emailed = "invite"
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "already" in msg or "registered" in msg or "exists" in msg:
                # Race: user appeared between list and invite — fall through to recovery.
                try:
                    listed = client.auth.admin.list_users()
                    users = getattr(listed, "users", None) or []
                    for u in users:
                        u_email = (getattr(u, "email", None) or "").lower()
                        if u_email == email:
                            user_id = str(getattr(u, "id", ""))
                            break
                except Exception as list_exc:  # noqa: BLE001
                    print(f"ERROR: invite failed and re-list failed: {list_exc}", file=sys.stderr)
                    return 1
                if not user_id:
                    print(f"ERROR: invite failed: {exc}", file=sys.stderr)
                    return 1
                try:
                    _send_recovery(url, key, email, redirect_to)
                except Exception as rec_exc:  # noqa: BLE001
                    print(f"ERROR: recovery failed: {rec_exc}", file=sys.stderr)
                    return 1
                emailed = "recovery"
                print("User already exists; sent recovery email so they can set a password.")
            else:
                print(f"ERROR: invite failed: {exc}", file=sys.stderr)
                return 1
        if not user_id:
            print("ERROR: invite returned no user id", file=sys.stderr)
            return 1
        if emailed == "invite":
            print(f"Invited {email} (password not set by this script — check invite email).")
    else:
        try:
            _send_recovery(url, key, email, redirect_to)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: recovery failed: {exc}", file=sys.stderr)
            return 1
        emailed = "recovery"
        print(f"User {email} already exists; sent recovery email + granting admin role.")

    try:
        client.table("user_roles").upsert(
            {"user_id": user_id, "app": APP_ID, "role": "admin"},
            on_conflict="user_id,app",
        ).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed writing user_roles: {exc}", file=sys.stderr)
        return 1

    print(f"Granted admin on {APP_ID} for user_id={user_id}")
    if emailed == "recovery":
        print("Open the recovery email → /auth/set-password → enroll MFA.")
    else:
        print("Open the invite email → /auth/set-password → enroll MFA.")
    print("Ensure Supabase Redirect URLs allowlist includes this redirectTo (see DEPLOYMENT.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
