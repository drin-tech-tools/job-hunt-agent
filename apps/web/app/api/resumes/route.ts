import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { resumeCreateSchema } from "@/lib/bff/schemas";
import { ZodError } from "zod";

export const runtime = "nodejs";

/** GET /api/resumes → FastAPI GET /resumes */
export async function GET() {
  return proxyJson("/resumes", { method: "GET" });
}

/** POST /api/resumes → FastAPI POST /resumes */
export async function POST(req: Request) {
  try {
    const json = await req.json();
    const body = resumeCreateSchema.parse(json);
    return proxyJson("/resumes", {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid JSON body" }, { status: 400 });
  }
}
