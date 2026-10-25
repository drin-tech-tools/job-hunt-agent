import { NextResponse } from "next/server";
import { ZodError } from "zod";

import { getApiUrl, internalApiHeaders } from "./api-base";

/** Proxy a JSON request to an allowlisted FastAPI path. */
export async function proxyJson(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const url = new URL(path, ensureTrailingSlash(getApiUrl()));
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const internal = internalApiHeaders();
  for (const [k, v] of Object.entries(internal)) {
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

function ensureTrailingSlash(base: string): string {
  return base.endsWith("/") ? base : `${base}/`;
}
