import { type NextRequest } from "next/server";

import { updateSession } from "@/lib/supabase/middleware";

/**
 * Auth wall for pages + BFF routes.
 *
 * Must use the Node.js runtime: Vercel Services does not support Edge Runtime
 * output (including default Edge middleware).
 */
export async function middleware(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  runtime: "nodejs",
  matcher: [
    /*
     * Match all paths except static assets and Next internals.
     * API routes are included so the wall applies; handlers re-check AAL2.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
