import { AuthError, requirePermission } from "@/lib/auth/session";
import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { ZodError, z } from "zod";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

const roleSchema = z.object({ role: z.enum(["admin", "client"]) });
const actionSchema = z.object({
  action: z.enum(["disable", "reset-mfa", "role"]),
  role: z.enum(["admin", "client"]).optional(),
});

/** PATCH /api/admin/users/:id — role / disable / reset-mfa */
export async function PATCH(req: Request, ctx: Ctx) {
  try {
    await requirePermission("manage_users");
    const { id } = await ctx.params;
    const json = await req.json();
    const body = actionSchema.parse(json);
    if (body.action === "role") {
      const role = roleSchema.parse({ role: body.role }).role;
      return proxyJson(`/admin/users/${encodeURIComponent(id)}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
    }
    if (body.action === "disable") {
      return proxyJson(`/admin/users/${encodeURIComponent(id)}/disable`, {
        method: "POST",
        body: "{}",
      });
    }
    return proxyJson(`/admin/users/${encodeURIComponent(id)}/reset-mfa`, {
      method: "POST",
      body: "{}",
    });
  } catch (err) {
    if (err instanceof AuthError) {
      return Response.json({ detail: err.message }, { status: err.status });
    }
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid request" }, { status: 400 });
  }
}

/** DELETE /api/admin/users/:id — remove user */
export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    await requirePermission("manage_users");
    const { id } = await ctx.params;
    return proxyJson(`/admin/users/${encodeURIComponent(id)}`, { method: "DELETE" });
  } catch (err) {
    if (err instanceof AuthError) {
      return Response.json({ detail: err.message }, { status: err.status });
    }
    return Response.json({ detail: "Forbidden" }, { status: 403 });
  }
}
