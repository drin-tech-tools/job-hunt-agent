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
  "/auth/callback",
];

function isAal1Path(pathname: string): boolean {
  return AAL1_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Carry cookies the Supabase client set on `supabaseResponse` (with their options) onto `target`. */
function copyCookies(from: NextResponse, target: NextResponse): void {
  from.cookies.getAll().forEach((c) => {
    target.cookies.set(c);
  });
}

function redirectWithCookies(
  request: NextRequest,
  supabaseResponse: NextResponse,
  pathname: string,
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  const redirectResponse = NextResponse.redirect(url);
  copyCookies(supabaseResponse, redirectResponse);
  return redirectResponse;
}

/**
 * BFF calls (`/api/*`) get a 401 JSON error; a redirect would be followed by `fetch` and
 * hand the client the HTML login page with a 200. Pages are redirected as before.
 */
function denyOrRedirect(
  request: NextRequest,
  supabaseResponse: NextResponse,
  pathname: string,
  detail: string,
): NextResponse {
  if (request.nextUrl.pathname.startsWith("/api/")) {
    const res = NextResponse.json({ detail }, { status: 401 });
    copyCookies(supabaseResponse, res);
    return res;
  }
  return redirectWithCookies(request, supabaseResponse, pathname);
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
    // The seam that sets the mock cookie must stay reachable when the cookie says "anonymous".
    if (pathname.startsWith("/api/e2e/")) return supabaseResponse;
    const raw = request.cookies.get(E2E_AUTH_COOKIE)?.value;
    const identity = identityFromCookieValue(raw);
    if (identity === "anonymous" || identity === null) {
      if (!isAal1Path(pathname) && pathname !== "/login") {
        return denyOrRedirect(request, supabaseResponse, "/login", "Unauthenticated");
      }
      return supabaseResponse;
    }
    if (identity.aal !== "aal2" && !isAal1Path(pathname)) {
      const dest =
        identity.aal === "aal1" && pathname !== "/mfa/setup" ? "/mfa/verify" : "/mfa/setup";
      // For mock, aal1 without factors → setup; with aal1 → verify
      return denyOrRedirect(request, supabaseResponse, dest, "AAL2 required (TOTP verified)");
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
      return denyOrRedirect(request, supabaseResponse, "/login", "Unauthenticated");
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
      return denyOrRedirect(request, supabaseResponse, "/login", "Unauthenticated");
    }
    return supabaseResponse;
  }

  const { data: aal } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
  const current = aal?.currentLevel ?? "aal1";
  const next = aal?.nextLevel ?? "aal1";

  // AAL1 + no factor enrolled → must set up MFA
  if (current === "aal1" && next === "aal1") {
    if (pathname !== "/mfa/setup" && pathname !== "/logout" && pathname !== "/auth/set-password") {
      return denyOrRedirect(request, supabaseResponse, "/mfa/setup", "AAL2 required (TOTP verified)");
    }
    return supabaseResponse;
  }

  // AAL1 + factor enrolled → must verify TOTP
  if (current === "aal1" && next === "aal2") {
    if (pathname !== "/mfa/verify" && pathname !== "/logout" && pathname !== "/auth/set-password") {
      return denyOrRedirect(request, supabaseResponse, "/mfa/verify", "AAL2 required (TOTP verified)");
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
