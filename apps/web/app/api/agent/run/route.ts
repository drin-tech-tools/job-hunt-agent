import { AuthError, requireAal2Session } from "@/lib/auth/session";
import { buildApiUrl, userAuthHeaders } from "@/lib/bff/api-base";
import { zodErrorResponse } from "@/lib/bff/proxy";
import { agentRunSchema } from "@/lib/bff/schemas";
import { ZodError } from "zod";

export const runtime = "nodejs";
/** Agent runs can take up to AGENT_OVERALL_TIMEOUT_S (~90s) plus SSE overhead. */
export const maxDuration = 300;

/**
 * POST /api/agent/run → FastAPI POST /agent/run
 *
 * Re-checks AAL2, then streams the upstream SSE body through without buffering.
 */
export async function POST(req: Request) {
  let accessToken: string;
  try {
    const session = await requireAal2Session();
    accessToken = session.accessToken;
  } catch (err) {
    if (err instanceof AuthError) {
      return Response.json({ detail: err.message }, { status: err.status });
    }
    return Response.json({ detail: "Unauthorized" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return Response.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  let parsed;
  try {
    parsed = agentRunSchema.parse(body);
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid request" }, { status: 400 });
  }

  const url = buildApiUrl("/agent/run");
  const headers = new Headers({
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    ...userAuthHeaders(accessToken),
  });

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(parsed),
      signal: req.signal,
      cache: "no-store",
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") {
      return new Response(null, { status: 499 });
    }
    const message = err instanceof Error ? err.message : "Upstream unreachable";
    return Response.json({ detail: message }, { status: 502 });
  }

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => upstream.statusText);
    return new Response(text || "Agent run failed", {
      status: upstream.status || 502,
      headers: {
        "Content-Type":
          upstream.headers.get("Content-Type") || "application/json",
      },
    });
  }

  const reader = upstream.body.getReader();
  const stream = new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) {
          controller.close();
          return;
        }
        controller.enqueue(value);
      } catch (err) {
        try {
          await reader.cancel();
        } catch {
          /* ignore */
        }
        controller.error(err);
      }
    },
    async cancel() {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
