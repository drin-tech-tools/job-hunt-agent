import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { E2E_AUTH_COOKIE, authBypassEnabled, identityFromCookieValue } from "@/lib/auth/mock";
import { supabasePublicConfigured } from "@/lib/supabase/env";

const AAL1_PATHS = [
  "/login",
  "/logout",
  "/mfa/setup",
  "/mfa/verify",
  "/auth/set-password",
];

function isAal1Path(pathname: string): boolean {
  return AAL1_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function redirectWithCookies(
  request: NextRequest,
  supabaseResponse: NextResponse,
  pathname: string,
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  const redirectResponse = NextResponse.redirect(url);
  supabaseResponse.cookies.getAll().forEach((c) => {
    redirectResponse.cookies.set(c.name, c.value);
  });
  return redirectResponse;
}

/**
 * Security wall: every page requires an authenticated AAL2 session, except
 * login / MFA / set-password / logout (usable at AAL1).
 */
export async function updateSession(request: NextRequest): Promise<NextResponse> {
  let supabaseResponse = NextResponse.next({ request });
  const { pathname } = request.nextUrl;

  // --- Mock auth seam (AUTH_BYPASS + AGENT_MOCK, never production) ---
  if (authBypassEnabled()) {
    const raw = request.cookies.get(E2E_AUTH_COOKIE)?.value;
    const identity = identityFromCookieValue(raw);
    if (identity === "anonymous" || identity === null) {
      if (!isAal1Path(pathname) && pathname !== "/login") {
        const url = request.nextUrl.clone();
        url.pathname = "/login";
        return NextResponse.redirect(url);
      }
      return supabaseResponse;
    }
    if (identity.aal !== "aal2" && !isAal1Path(pathname)) {
      const dest =
        identity.aal === "aal1" && pathname !== "/mfa/setup" ? "/mfa/verify" : "/mfa/setup";
      // For mock, aal1 without factors → setup; with aal1 → verify
      const url = request.nextUrl.clone();
      url.pathname = dest === "/mfa/verify" ? "/mfa/verify" : "/mfa/setup";
      return NextResponse.redirect(url);
    }
    if (identity.aal === "aal2" && (pathname === "/login" || pathname.startsWith("/mfa/"))) {
      const url = request.nextUrl.clone();
      url.pathname = "/";
      return NextResponse.redirect(url);
    }
    return supabaseResponse;
  }

  if (!supabasePublicConfigured()) {
    // Misconfigured prod — fail closed except login page (shows config error).
    if (!isAal1Path(pathname)) {
      return redirectWithCookies(request, supabaseResponse, "/login");
    }
    return supabaseResponse;
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    if (!isAal1Path(pathname)) {
      return redirectWithCookies(request, supabaseResponse, "/login");
    }
    return supabaseResponse;
  }

  const { data: aal } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
  const current = aal?.currentLevel ?? "aal1";
  const next = aal?.nextLevel ?? "aal1";

  // AAL1 + no factor enrolled → must set up MFA
  if (current === "aal1" && next === "aal1") {
    if (pathname !== "/mfa/setup" && pathname !== "/logout" && pathname !== "/auth/set-password") {
      return redirectWithCookies(request, supabaseResponse, "/mfa/setup");
    }
    return supabaseResponse;
  }

  // AAL1 + factor enrolled → must verify TOTP
  if (current === "aal1" && next === "aal2") {
    if (pathname !== "/mfa/verify" && pathname !== "/logout" && pathname !== "/auth/set-password") {
      return redirectWithCookies(request, supabaseResponse, "/mfa/verify");
    }
    return supabaseResponse;
  }

  // AAL2 — block lingering on auth pages
  if (current === "aal2") {
    if (pathname === "/login" || pathname.startsWith("/mfa/")) {
      return redirectWithCookies(request, supabaseResponse, "/");
    }
  }

  return supabaseResponse;
}
