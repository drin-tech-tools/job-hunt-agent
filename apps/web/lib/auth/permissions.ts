/**
 * Central RBAC permission matrix for app `job-hunt-agent`.
 * Mirrored in `apps/api/app/auth/permissions.py`.
 */

export const APP_ID = "job-hunt-agent" as const;

export type Role = "admin" | "client";

export type Permission =
  | "manage_own_resume"
  | "manage_any_resume"
  | "run_agent"
  | "manage_own_tracker"
  | "manage_any_tracker"
  | "view_own_agent_runs"
  | "view_any_agent_runs"
  | "manage_users";

const ROLE_PERMISSIONS: Record<Role, ReadonlySet<Permission>> = {
  client: new Set([
    "manage_own_resume",
    "run_agent",
    "manage_own_tracker",
    "view_own_agent_runs",
  ]),
  admin: new Set([
    "manage_own_resume",
    "manage_any_resume",
    "run_agent",
    "manage_own_tracker",
    "manage_any_tracker",
    "view_own_agent_runs",
    "view_any_agent_runs",
    "manage_users",
  ]),
};

export function can(role: Role | string | null | undefined, permission: Permission): boolean {
  if (role !== "admin" && role !== "client") return false;
  return ROLE_PERMISSIONS[role].has(permission);
}

export function isAdmin(role: Role | string | null | undefined): boolean {
  return role === "admin";
}
