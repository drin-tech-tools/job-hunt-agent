"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

export default function MfaVerifyPage() {
  const router = useRouter();
  const [factorId, setFactorId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "1") {
        setFactorId("mock-factor");
        return;
      }
      const supabase = createClient();
      const { data, error: listError } = await supabase.auth.mfa.listFactors();
      if (cancelled) return;
      if (listError) {
        setError(listError.message);
        return;
      }
      const totp = data.totp?.[0];
      if (!totp) {
        router.replace("/mfa/setup");
        return;
      }
      setFactorId(totp.id);
    })().catch((err) => {
      if (!cancelled) setError(err instanceof Error ? err.message : "Failed to list factors");
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    if (!factorId) return;
    setPending(true);
    setError(null);
    try {
      if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "1") {
        document.cookie = "jh-e2e-auth=mock.mock-admin.admin.aal2; path=/";
        router.replace("/");
        router.refresh();
        return;
      }
      const supabase = createClient();
      const challenge = await supabase.auth.mfa.challenge({ factorId });
      if (challenge.error) {
        setError(challenge.error.message);
        return;
      }
      const verified = await supabase.auth.mfa.verify({
        factorId,
        challengeId: challenge.data.id,
        code,
      });
      if (verified.error) {
        setError(verified.error.message);
        return;
      }
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-md pt-10">
      <h1
        className="text-2xl font-semibold"
        style={{ fontFamily: "var(--font-display)" }}
        data-testid="mfa-verify-heading"
      >
        Two-factor verification
      </h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Enter the 6-digit code from your authenticator app.
      </p>
      <form onSubmit={onVerify} className="mt-6 space-y-4" data-testid="mfa-verify-form">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Authentication code</span>
          <input
            data-testid="mfa-code"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-1)] px-3 py-2 tracking-widest"
          />
        </label>
        {error ? (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          data-testid="mfa-verify-submit"
          disabled={pending || !factorId}
          className="w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-black disabled:opacity-60"
        >
          {pending ? "Verifying…" : "Verify"}
        </button>
      </form>
    </div>
  );
}
