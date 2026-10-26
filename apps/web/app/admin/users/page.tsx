"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

type UserRow = {
  id: string;
  email?: string | null;
  role?: "admin" | "client" | null;
  banned?: boolean;
  factors?: number;
  /** Set when Supabase could not send the email; admin shares it manually. */
  invite_link?: string | null;
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "client">("client");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    const res = await fetch("/api/admin/users");
    if (res.status === 403 || res.status === 401) {
      setForbidden(true);
      setUsers([]);
      return;
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.detail || "Failed to load users");
      return;
    }
    setForbidden(false);
    setUsers(await res.json());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function invite(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    setError(null);
    setInviteLink(null);
    const res = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "Invite failed");
      return;
    }
    const created: UserRow = await res.json();
    if (created.invite_link) {
      setStatus(`The invite email to ${email} could not be sent. Share this one-time link with them directly:`);
      setInviteLink(created.invite_link);
    } else {
      setStatus(`Invite sent to ${email}`);
    }
    setEmail("");
    await load();
  }

  async function act(userId: string, action: "disable" | "reset-mfa" | "role", nextRole?: "admin" | "client") {
    setError(null);
    const res = await fetch(`/api/admin/users/${encodeURIComponent(userId)}`, {
      method: action === "role" || action === "disable" || action === "reset-mfa" ? "PATCH" : "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, role: nextRole }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "Action failed");
      return;
    }
    await load();
  }

  async function remove(userId: string) {
    setError(null);
    const res = await fetch(`/api/admin/users/${encodeURIComponent(userId)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "Remove failed");
      return;
    }
    await load();
  }

  if (forbidden) {
    return (
      <div data-testid="admin-forbidden">
        <h1 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>
          Admin
        </h1>
        <p className="mt-4 text-sm text-red-400">You do not have permission to manage users.</p>
      </div>
    );
  }

  return (
    <div data-testid="admin-users-page">
      <h1 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>
        Users
      </h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Invite-only access. Assign admin or client. No public signup.
      </p>

      <form onSubmit={invite} className="mt-8 flex flex-wrap items-end gap-3" data-testid="invite-form">
        <label className="text-sm">
          <span className="text-[var(--muted)]">Invite email</span>
          <input
            data-testid="invite-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-64 rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="text-[var(--muted)]">Role</span>
          <select
            data-testid="invite-role"
            value={role}
            onChange={(e) => setRole(e.target.value as "admin" | "client")}
            className="mt-1 block rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          >
            <option value="client">client</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button
          type="submit"
          data-testid="invite-submit"
          className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-black"
        >
          Invite
        </button>
      </form>

      {status ? <p className="mt-3 text-sm text-emerald-400">{status}</p> : null}
      {inviteLink ? (
        <input
          data-testid="invite-link"
          readOnly
          value={inviteLink}
          onFocus={(e) => e.currentTarget.select()}
          className="mt-2 block w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2 text-xs"
        />
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      <ul className="mt-8 divide-y divide-[var(--line)]" data-testid="users-list">
        {users.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div>
              <div className="font-medium">{u.email || u.id}</div>
              <div className="text-xs text-[var(--muted)]">
                {u.role || "no role"}
                {u.banned ? " · disabled" : ""}
                {typeof u.factors === "number" ? ` · MFA factors: ${u.factors}` : ""}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md border border-[var(--line)] px-2 py-1 text-xs"
                onClick={() => act(u.id, "role", u.role === "admin" ? "client" : "admin")}
              >
                Toggle role
              </button>
              <button
                type="button"
                className="rounded-md border border-[var(--line)] px-2 py-1 text-xs"
                onClick={() => act(u.id, "reset-mfa")}
              >
                Reset MFA
              </button>
              <button
                type="button"
                className="rounded-md border border-[var(--line)] px-2 py-1 text-xs"
                onClick={() => act(u.id, "disable")}
              >
                Disable
              </button>
              <button
                type="button"
                className="rounded-md border border-red-500/40 px-2 py-1 text-xs text-red-300"
                onClick={() => remove(u.id)}
              >
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
