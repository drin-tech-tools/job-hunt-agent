import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  E2E_AUTH_COOKIE,
  authBypassEnabled,
  identityFromCookieValue,
  type MockIdentity,
} from "@/lib/auth/mock";
import { can, type Permission, type Role } from "@/lib/auth/permissions";
import { APP_ID } from "@/lib/auth/permissions";
import { supabasePublicConfigured } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

export type SessionIdentity = {
  userId: string;
  email: string | null;
  role: Role;
  aal: "aal1" | "aal2";
  accessToken: string;
  isMock: boolean;
};

export class AuthError extends Error {
  status: number;
  constructor(message: string, status = 401) {
    super(message);
    this.status = status;
  }
}

async function loadRole(userId: string): Promise<Role | null> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("user_roles")
    .select("role")
    .eq("user_id", userId)
    .eq("app", APP_ID)
    .maybeSingle();
  if (error || !data) return null;
  if (data.role === "admin" || data.role === "client") return data.role;
  return null;
}

async function mockIdentityFromCookies(): Promise<MockIdentity | "anonymous" | null> {
  if (!authBypassEnabled()) return null;
  const jar = await cookies();
  return identityFromCookieValue(jar.get(E2E_AUTH_COOKIE)?.value);
}

/**
 * Resolve the current session. Returns null when unauthenticated.
 * Does not enforce AAL2 — callers choose.
 */
export async function getSessionIdentity(): Promise<SessionIdentity | null> {
  const mock = await mockIdentityFromCookies();
  if (mock === "anonymous") return null;
  if (mock) {
    return {
      userId: mock.id,
      email: mock.email,
      role: mock.role,
      aal: mock.aal,
      accessToken: mock.accessToken,
      isMock: true,
    };
  }

  if (!supabasePublicConfigured()) {
    return null;
  }

  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) return null;

  const { data: aalData } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
  const current = (aalData?.currentLevel || "aal1") as "aal1" | "aal2";

  const {
    data: { session },
  } = await supabase.auth.getSession();
  const accessToken = session?.access_token;
  if (!accessToken) return null;

  const role = await loadRole(user.id);
  if (!role) {
    // Authenticated but no app role yet — treat as no access for protected routes.
    return {
      userId: user.id,
      email: user.email ?? null,
      role: "client",
      aal: current,
      accessToken,
      isMock: false,
    };
  }

  return {
    userId: user.id,
    email: user.email ?? null,
    role,
    aal: current,
    accessToken,
    isMock: false,
  };
}

/** Require AAL2 + assigned role. Throws AuthError. */
export async function requireAal2Session(): Promise<SessionIdentity> {
  const identity = await getSessionIdentity();
  if (!identity) {
    throw new AuthError("Unauthenticated", 401);
  }
  if (identity.aal !== "aal2") {
    throw new AuthError("AAL2 required (TOTP verified)", 401);
  }
  return identity;
}

export async function requirePermission(permission: Permission): Promise<SessionIdentity> {
  const identity = await requireAal2Session();
  // Re-load role from DB for real users; mock already has role.
  if (!identity.isMock) {
    const role = await loadRole(identity.userId);
    if (!role || !can(role, permission)) {
      throw new AuthError("Forbidden", 403);
    }
    return { ...identity, role };
  }
  if (!can(identity.role, permission)) {
    throw new AuthError("Forbidden", 403);
  }
  return identity;
}

export function authErrorResponse(err: unknown): NextResponse {
  if (err instanceof AuthError) {
    return NextResponse.json({ detail: err.message }, { status: err.status });
  }
  const message = err instanceof Error ? err.message : "Unauthorized";
  return NextResponse.json({ detail: message }, { status: 401 });
}
