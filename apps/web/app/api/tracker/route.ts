import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { trackerCreateSchema } from "@/lib/bff/schemas";
import { ZodError } from "zod";

export const runtime = "nodejs";

/** GET /api/tracker → FastAPI GET /tracker */
export async function GET() {
  return proxyJson("/tracker", { method: "GET" });
}

/** POST /api/tracker → FastAPI POST /tracker */
export async function POST(req: Request) {
  try {
    const json = await req.json();
    const body = trackerCreateSchema.parse(json);
    return proxyJson("/tracker", {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid JSON body" }, { status: 400 });
  }
}
