import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { idParamSchema } from "@/lib/bff/schemas";
import { ZodError } from "zod";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** DELETE /api/resumes/:id → FastAPI DELETE /resumes/:id */
export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    const { id } = await ctx.params;
    const resumeId = idParamSchema.parse(id);
    return proxyJson(`/resumes/${encodeURIComponent(resumeId)}`, {
      method: "DELETE",
    });
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid id" }, { status: 400 });
  }
}
