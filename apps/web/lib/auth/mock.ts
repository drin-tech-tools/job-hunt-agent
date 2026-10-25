/**
 * Test-only auth seam for Cucumber / local demos.
 *
 * Enabled when AUTH_BYPASS=1 AND AGENT_MOCK=1 (API / Route Handlers), or
 * NEXT_PUBLIC_AUTH_BYPASS=1 (Edge middleware — only public env is reliably inlined).
 * Never when VERCEL_ENV=production.
 *
 * Cookie `jh-e2e-auth` values:
 *   - absent → default mock admin AAL2 (existing journeys keep working)
 *   - `anonymous` → unauthenticated
 *   - `mock.<userId>.<role>.<aal>` → explicit identity (same as API bearer)
 */

export const E2E_AUTH_COOKIE = "jh-e2e-auth";

export type MockIdentity = {
  id: string;
  email: string;
  role: "admin" | "client";
  aal: "aal1" | "aal2";
  accessToken: string;
};

export function authBypassEnabled(): boolean {
  if (process.env.VERCEL_ENV === "production") return false;

  // Edge middleware: NEXT_PUBLIC_* is reliably available.
  if (
    process.env.NEXT_PUBLIC_AUTH_BYPASS === "1" ||
    process.env.NEXT_PUBLIC_AUTH_BYPASS === "true"
  ) {
    return true;
  }

  // Server / API-aligned: require both AUTH_BYPASS and AGENT_MOCK.
  const bypass = process.env.AUTH_BYPASS === "1" || process.env.AUTH_BYPASS === "true";
  const mock = process.env.AGENT_MOCK === "1" || process.env.AGENT_MOCK === "true";
  return bypass && mock;
}

export function parseMockToken(token: string): MockIdentity | null {
  if (!token.startsWith("mock.")) return null;
  const parts = token.slice("mock.".length).split(".");
  if (parts.length < 2) return null;
  const [id, role, aal = "aal2"] = parts;
  if (role !== "admin" && role !== "client") return null;
  if (aal !== "aal1" && aal !== "aal2") return null;
  return {
    id,
    email: `${id}@example.test`,
    role,
    aal,
    accessToken: token.startsWith("mock.") ? token : `mock.${id}.${role}.${aal}`,
  };
}

export function identityFromCookieValue(
  raw: string | undefined,
): MockIdentity | "anonymous" | null {
  if (!authBypassEnabled()) return null;
  if (raw === "anonymous") return "anonymous";
  if (!raw || raw === "default") {
    return {
      id: "mock-admin",
      email: "admin@example.test",
      role: "admin",
      aal: "aal2",
      accessToken: "mock.mock-admin.admin.aal2",
    };
  }
  return parseMockToken(raw.startsWith("mock.") ? raw : `mock.${raw}`);
}

export function mockBearerFor(identity: MockIdentity): string {
  return identity.accessToken.startsWith("mock.")
    ? identity.accessToken
    : `mock.${identity.id}.${identity.role}.${identity.aal}`;
}
