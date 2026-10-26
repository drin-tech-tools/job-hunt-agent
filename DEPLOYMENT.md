# Deployment (single Vercel project — Services)

Deploy this monorepo as **one Vercel project** using [Vercel Services](https://vercel.com/docs/services) (Beta): a public Next.js `web` service and an **internal** FastAPI `api` service. The browser only talks to `web`; `web` calls `api` over a private service binding (`API_URL`). Skip Vercel’s Supabase marketplace integration — configure Supabase manually.

> **Hobby requirement:** the GitHub repository must be **public** for org/team Hobby deploys from a connected repo.

> **Same Supabase project:** use the owner’s existing **rag-doc-chatbot** Supabase project so `public.user_roles` is shared across apps.

## 1. Supabase Auth + schema

1. Open the existing Supabase project (rag-doc-chatbot / job-hunt-agent).
2. **SQL Editor** → run [`supabase/migrations/001_init.sql`](supabase/migrations/001_init.sql) (if not already applied).
3. Run [`supabase/migrations/002_auth_rbac.sql`](supabase/migrations/002_auth_rbac.sql) — creates shared `user_roles`, ownership columns, and RLS (idempotent `create table if not exists`).
4. **Authentication → Providers → Email**: enable Email. **Disable** public sign-ups (“Allow new users to sign up” = off). Invites are admin-only via the service role.
5. **Authentication → Multi-Factor Auth**: enable **TOTP** (App Authenticator). Enforcement is in app middleware (AAL2 required). The middleware must use `runtime: "nodejs"` — Vercel Services rejects Edge Runtime output.
6. **Authentication → URL configuration** (required — wrong allowlist is why invites fall back to Site URL with `#access_token=…` on `/login`):
   - **Site URL**: `https://job-hunt-agent-eta.vercel.app`
   - **Redirect URLs** — add all of these:

     | URL | Why |
     |---|---|
     | `https://job-hunt-agent-eta.vercel.app/auth/callback` | PKCE / callback landing |
     | `https://job-hunt-agent-eta.vercel.app/auth/callback?next=/auth/set-password` | Invite + recovery `redirectTo` used by bootstrap + admin invite |
     | `https://job-hunt-agent-eta.vercel.app/**` | Safety net so Site URL fallback + hash landings still allow the app origin |
     | `http://localhost:3000/auth/callback` | Local PKCE / callback |
     | `http://localhost:3000/auth/callback?next=/auth/set-password` | Local invite / recovery |
     | `http://localhost:3000/**` | Local safety net |

   - After saving, re-run `uv run python scripts/bootstrap_admin.py` so a fresh invite/recovery email is issued (old links are single-use).
7. **Email templates** (recommended): prefer `{{ .RedirectTo }}` over `{{ .SiteURL }}` for the CTA href so invite/recovery honor `redirectTo`. The app also accepts implicit-flow `#access_token` on `/login` and `/auth/callback` if a link still lands on Site URL.
8. **Project Settings → API Keys** — copy:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_URL`
   - **Publishable** key → `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (browser + SSR)
   - **Secret** key (`sb_secret_...`) → `SUPABASE_SERVICE_ROLE_KEY` (API + admin invite only; never `NEXT_PUBLIC_*`)

## 2. Bootstrap the first admin

Never hardcode or print passwords. The bootstrap script **invites** `ADMIN_EMAIL` (or, if the user already exists / invite was consumed, sends a **recovery** email to the same `redirectTo`) and upserts `admin` for `job-hunt-agent`.

```bash
cd apps/api
export SUPABASE_URL=https://xxxx.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
export ADMIN_EMAIL=you@example.com
# Optional — defaults to https://job-hunt-agent-eta.vercel.app
# export SITE_URL=https://job-hunt-agent-eta.vercel.app
uv run python scripts/bootstrap_admin.py
```

`redirectTo` is always `${SITE_URL}/auth/callback?next=/auth/set-password`. Open the invite (or recovery) email → **/auth/set-password** → **/mfa/setup** (scan QR, verify TOTP) → app at AAL2. Re-run the script anytime to resend a recovery link for an existing admin.

### Invite troubleshooting

| Symptom | What to do |
|---|---|
| Landed on `/login#access_token=…` / cannot set password | Redirect allowlist was incomplete so Auth fell back to Site URL. Confirm Redirect URLs (table above), re-run bootstrap, open the **new** email. The app now consumes hash tokens on `/login` and routes invite/recovery to set-password. |
| Invite email missing | Check Supabase Auth → Users and spam; confirm Site URL + Redirect URLs. |
| `Invite failed: Error sending invite email` | Supabase's built-in mailer only delivers to your project's team members and is heavily rate-limited. Set up custom SMTP (**Authentication → SMTP Settings**, e.g. Resend/Postmark) so any invitee gets the email. Until then, the Users page falls back to a one-time invite link you copy and share manually. |
| Old invite link expired / already used | Re-run `bootstrap_admin.py` — it sends a **recovery** email for existing users. |

## 3. Gemini API key (free tier)

1. Create an API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Set `GEMINI_API_KEY` on the Vercel project (shared across services; only `api` needs it at runtime).
3. Optionally set `GEMINI_CHAT_MODEL` to pin a model. Otherwise the API tries, in order:
   - `gemini-3.5-flash-lite`
   - `gemini-3.1-flash-lite`
   - `gemini-flash-latest`
   - `gemini-3.8-flash`  
   and falls back on 404 / timeout (2.5 models are often unavailable to new users).

## 4. Vercel — import the repo once

In the Vercel dashboard, **Import** this GitHub repository as a **single project**. Leave the Root Directory empty (repo root). Vercel reads [`vercel.json`](vercel.json):

| Service | Root | Framework | Public? |
| --- | --- | --- | --- |
| `web` | `apps/web` | Next.js | Yes — catch-all rewrite |
| `api` | `apps/api` | FastAPI | No — binding only |

### Environment variables (Production + Preview)

```
GEMINI_API_KEY=...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
ADMIN_EMAIL=you@example.com
SITE_URL=https://job-hunt-agent-eta.vercel.app
```

Optional:

```
INTERNAL_API_TOKEN=<long random secret>
GEMINI_CHAT_MODEL=
JSEARCH_API_KEY=
AGENT_MOCK=
```

### Do **not** set

- `API_URL` — injected automatically by the `web` → `api` service binding at **function runtime** (not builds, not middleware).
- `NEXT_PUBLIC_API_URL` — removed; the browser calls same-origin `/api/*` BFF routes only.
- `AUTH_BYPASS` / `NEXT_PUBLIC_AUTH_BYPASS` — **never** on Production (`VERCEL_ENV=production`). Test-only seam for Cucumber (`AUTH_BYPASS=1` + `AGENT_MOCK=1`).
- `ALLOWED_ORIGINS` — unused in production (API is not on the public internet).

### `INTERNAL_API_TOKEN` (optional, recommended)

Defense in depth on top of network isolation:

1. Generate a long random secret and set `INTERNAL_API_TOKEN` on the project.
2. The Next.js BFF sends it as `X-Internal-Api-Token` on every upstream call **and** forwards `Authorization: Bearer <user access token>`.
3. When the env is set, FastAPI rejects requests that omit or mismatch the internal header.
4. FastAPI **also** requires a valid Supabase user JWT at AAL2 — the internal token alone is never enough.

## 5. Smoke check

```bash
# Unauthenticated browser hits should redirect to /login
# After AAL2 login:
curl -H "Cookie: ..." https://YOUR_PROJECT.vercel.app/api/health

# FastAPI must NOT be reachable publicly (no rewrite targets api)
```

Open `https://YOUR_PROJECT.vercel.app` → sign in → MFA → Resume → Agent.

## 6. What not to do

- Do **not** enable Vercel’s one-click Supabase integration (env names / keys differ).
- Do **not** commit `.env` files — only `.env.example`.
- Do **not** put `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, or `INTERNAL_API_TOKEN` in client bundles (`NEXT_PUBLIC_*`).
- Do **not** add a top-level rewrite to `api` — that would make FastAPI public and defeat the BFF.
- Do **not** enable public sign-ups or skip TOTP MFA.
- Do **not** set `AUTH_BYPASS` in Production.

## Local development

### Preferred — `vercel dev` (bindings)

```bash
vercel dev
# or: vercel dev -L
```

### Fallback — two processes

```bash
# Terminal 1 — API
cd apps/api && uv sync --group dev
# For auth’d local API without real JWTs during demos:
# AUTH_BYPASS=1 AGENT_MOCK=1
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Web
cd apps/web
cp .env.example .env.local
npm install && npm run dev
```

E2E orchestration (`npm run test:e2e`) starts both with `AGENT_MOCK=1` + `AUTH_BYPASS=1` and a cookie-based mock-auth seam.

## Owner setup checklist (exact)

1. Reuse the rag-doc-chatbot Supabase project.
2. Run SQL migrations `001_init.sql` then `002_auth_rbac.sql`.
3. Disable public sign-ups; enable Email + TOTP MFA.
4. Set Site URL + Redirect URLs (exact table in section 1 — include `/auth/callback?next=/auth/set-password`).
5. Set Vercel env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `ADMIN_EMAIL`, `SITE_URL`, optional `INTERNAL_API_TOKEN`.
6. Run `uv run python scripts/bootstrap_admin.py` with `ADMIN_EMAIL` (sends invite or recovery).
7. Accept invite/recovery → **/auth/set-password** → enroll TOTP → use the app.
8. Invite additional users from `/admin/users` (admin only; same `redirectTo`).

## Local ↔ prod parity

| Concern | Local | Prod |
| --- | --- | --- |
| Ingress | `web` on :3000; `api` on :8000 | Only `web` public; `api` via binding |
| `API_URL` | Binding (`vercel dev`) or `http://127.0.0.1:8000` | Service binding (auto) |
| Auth | Real Supabase or `AUTH_BYPASS`+`AGENT_MOCK` | Supabase session AAL2 only |
| Supabase | Required for real auth; memory OK with bypass | Required |
| Gemini | Optional — heuristic / `AGENT_MOCK` | Required for LLM planning |
| `INTERNAL_API_TOKEN` | Optional | Recommended |
| CORS | Harmless localhost default | Not needed |
