import { NextResponse } from "next/server";
import { ZodError } from "zod";

import { AuthError, requireAal2Session } from "@/lib/auth/session";
import { buildApiUrl, userAuthHeaders } from "./api-base";

/**
 * Proxy a JSON request to an allowlisted FastAPI path.
 * Re-checks AAL2 session in the Route Handler, then forwards Bearer + internal token.
 */
export async function proxyJson(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let accessToken: string;
  try {
    const session = await requireAal2Session();
    accessToken = session.accessToken;
  } catch (err) {
    if (err instanceof AuthError) {
      return NextResponse.json({ detail: err.message }, { status: err.status });
    }
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const url = buildApiUrl(path);
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const auth = userAuthHeaders(accessToken);
  for (const [k, v] of Object.entries(auth)) {
    headers.set(k, v);
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      ...init,
      headers,
      // Do not forward browser cookies to the internal service.
      cache: "no-store",
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upstream unreachable";
    return NextResponse.json({ detail: message }, { status: 502 });
  }

  const contentType = upstream.headers.get("Content-Type") || "application/json";
  const body = await upstream.arrayBuffer();
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}

export function zodErrorResponse(err: ZodError): NextResponse {
  return NextResponse.json(
    { detail: "Invalid request", issues: err.flatten() },
    { status: 400 },
  );
}
