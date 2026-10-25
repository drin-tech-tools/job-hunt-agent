import { NextResponse } from "next/server";

import { E2E_AUTH_COOKIE, authBypassEnabled } from "@/lib/auth/mock";
import { supabasePublicConfigured } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

/** GET /logout — sign out and clear session cookies. */
export async function GET(request: Request) {
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
