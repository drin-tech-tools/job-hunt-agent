"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

/**
 * Invite acceptance: user lands here from the invite email link (Supabase
 * recovery / invite session already in cookies), sets a password, then MFA setup.
 */
export default function SetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 10) {
      setError("Password must be at least 10 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    try {
      if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "1") {
        router.replace("/mfa/setup");
        return;
      }
      const supabase = createClient();
      const { error: updateError } = await supabase.auth.updateUser({ password });
      if (updateError) {
        setError(updateError.message);
        return;
      }
      router.replace("/mfa/setup");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not set password");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-md pt-10">
      <h1
        className="text-2xl font-semibold"
        style={{ fontFamily: "var(--font-display)" }}
        data-testid="set-password-heading"
      >
        Set your password
      </h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Complete your invite, then enroll TOTP two-factor authentication.
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4" data-testid="set-password-form">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">New password</span>
          <input
            data-testid="set-password-input"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Confirm password</span>
          <input
            data-testid="set-password-confirm"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          />
        </label>
        {error ? (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          data-testid="set-password-submit"
          disabled={pending}
          className="w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-black disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save and continue"}
        </button>
      </form>
    </div>
  );
}
