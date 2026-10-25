import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { idParamSchema, trackerUpdateSchema } from "@/lib/bff/schemas";
import { ZodError } from "zod";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** PATCH /api/tracker/:id → FastAPI PATCH /tracker/:id */
export async function PATCH(req: Request, ctx: Ctx) {
  try {
    const { id } = await ctx.params;
    const itemId = idParamSchema.parse(id);
    const json = await req.json();
    const body = trackerUpdateSchema.parse(json);
    return proxyJson(`/tracker/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid request" }, { status: 400 });
  }
}

/** DELETE /api/tracker/:id → FastAPI DELETE /tracker/:id */
export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    const { id } = await ctx.params;
    const itemId = idParamSchema.parse(id);
    return proxyJson(`/tracker/${encodeURIComponent(itemId)}`, {
      method: "DELETE",
    });
  } catch (err) {
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid id" }, { status: 400 });
  }
}
