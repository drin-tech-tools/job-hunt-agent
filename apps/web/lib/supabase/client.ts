"use client";

import { createBrowserClient } from "@supabase/ssr";

import { getSupabasePublishableKey, getSupabaseUrl } from "./env";

export function createClient() {
  // Disable automatic URL detection — AuthUrlHandler /auth/callback owns
  // hash + token_hash + PKCE so we can route invite/recovery to set-password.
  return createBrowserClient(getSupabaseUrl(), getSupabasePublishableKey(), {
    auth: {
      detectSessionInUrl: false,
      flowType: "pkce",
    },
  });
}
