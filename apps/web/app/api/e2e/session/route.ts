import { NextResponse } from "next/server";

import { E2E_AUTH_COOKIE, authBypassEnabled } from "@/lib/auth/mock";

/**
 * Test-only helper to set the mock-auth cookie on the response host.
 * Disabled unless AUTH_BYPASS / NEXT_PUBLIC_AUTH_BYPASS is enabled (never production).
 *
 * GET /api/e2e/session?as=anonymous|admin|client
 */
export async function GET(request: Request) {
  if (!authBypassEnabled()) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const url = new URL(request.url);
  const as = url.searchParams.get("as") || "admin";

  let value: string;
  if (as === "anonymous") {
    value = "anonymous";
  } else if (as === "client") {
    value = "mock.user-client-1.client.aal2";
  } else if (as === "admin") {
    value = "mock.mock-admin.admin.aal2";
  } else if (as.startsWith("mock.")) {
    value = as;
  } else {
    return NextResponse.json({ detail: "Invalid as=" }, { status: 400 });
  }

  const res = NextResponse.json({ ok: true, as, cookie: E2E_AUTH_COOKIE });
  res.cookies.set(E2E_AUTH_COOKIE, value, {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
  });
  return res;
}
