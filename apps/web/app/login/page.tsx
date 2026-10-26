"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(() => {
    const raw = params.get("error");
    if (!raw) return null;
    if (raw === "auth_callback_failed") return "Sign-in link failed. Try again.";
    return raw;
  });
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      // Mock / e2e seam: AUTH_BYPASS pages still render login UI; cookie set via test helpers.
      if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "1") {
        document.cookie = "jh-e2e-auth=mock.mock-admin.admin.aal2; path=/";
        router.replace("/");
        router.refresh();
        return;
      }
      const supabase = createClient();
      const { error: signError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signError) {
        setError(signError.message);
        return;
      }
      const { data: aal } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
      if (aal?.currentLevel === "aal2") {
        router.replace("/");
      } else if (aal?.nextLevel === "aal2") {
        router.replace("/mfa/verify");
      } else {
        router.replace("/mfa/setup");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-md pt-10">
      <h1
        className="text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
        data-testid="login-heading"
      >
        Job Hunt Agent
      </h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Sign in with your invite email and password. Public signup is disabled.
      </p>
      <form
        onSubmit={onSubmit}
        className="mt-8 space-y-4"
        data-testid="login-form"
      >
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Email</span>
          <input
            data-testid="login-email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Password</span>
          <input
            data-testid="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2"
          />
        </label>
        {error ? (
          <p className="text-sm text-red-400" data-testid="login-error" role="alert">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          data-testid="login-submit"
          disabled={pending}
          className="w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-black disabled:opacity-60"
        >
          {pending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-md pt-10">
          <h1
            className="text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Job Hunt Agent
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">Loading…</p>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
