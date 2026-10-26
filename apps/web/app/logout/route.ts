import { NextResponse } from "next/server";

import { E2E_AUTH_COOKIE, authBypassEnabled } from "@/lib/auth/mock";
import { isPrefetchRequest } from "@/lib/bff/prefetch";
import { supabasePublicConfigured } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

/** GET /logout — sign out and clear session cookies. */
export async function GET(request: Request) {
  // Next.js may prefetch links to this route; that must never end the session.
  if (isPrefetchRequest(request.headers)) {
    return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
  }

  const url = new URL("/login", request.url);
  const res = NextResponse.redirect(url);

  if (authBypassEnabled()) {
    res.cookies.set(E2E_AUTH_COOKIE, "anonymous", { path: "/" });
  }

  if (supabasePublicConfigured()) {
    try {
      const supabase = await createClient();
      await supabase.auth.signOut();
    } catch {
      /* best-effort */
    }
  }

  return res;
}
