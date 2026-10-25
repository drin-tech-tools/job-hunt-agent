import { AuthError, requirePermission } from "@/lib/auth/session";
import { proxyJson, zodErrorResponse } from "@/lib/bff/proxy";
import { ZodError, z } from "zod";

export const runtime = "nodejs";

const inviteSchema = z.object({
  email: z.string().email(),
  role: z.enum(["admin", "client"]).default("client"),
});

/** GET /api/admin/users — list users (admin only; re-checked in handler + API). */
export async function GET() {
  try {
    await requirePermission("manage_users");
  } catch (err) {
    if (err instanceof AuthError) {
      return Response.json({ detail: err.message }, { status: err.status });
    }
    return Response.json({ detail: "Forbidden" }, { status: 403 });
  }
  return proxyJson("/admin/users", { method: "GET" });
}

/** POST /api/admin/users — invite by email. */
export async function POST(req: Request) {
  try {
    await requirePermission("manage_users");
    const json = await req.json();
    const body = inviteSchema.parse(json);
    return proxyJson("/admin/users/invite", {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof AuthError) {
      return Response.json({ detail: err.message }, { status: err.status });
    }
    if (err instanceof ZodError) return zodErrorResponse(err);
    return Response.json({ detail: "Invalid request" }, { status: 400 });
  }
}
