# Deployment (single Vercel project — Services)

Deploy this monorepo as **one Vercel project** using [Vercel Services](https://vercel.com/docs/services) (Beta): a public Next.js `web` service and an **internal** FastAPI `api` service. The browser only talks to `web`; `web` calls `api` over a private service binding (`API_URL`). Skip Vercel’s Supabase marketplace integration — configure Supabase manually.

> **Hobby requirement:** the GitHub repository must be **public** for org/team Hobby deploys from a connected repo.

## 1. Supabase (free project)

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** → New query → paste and run [`supabase/migrations/001_init.sql`](supabase/migrations/001_init.sql).
3. Open **Project Settings → API Keys**.
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **Secret key** (`sb_secret_...`) → `SUPABASE_SERVICE_ROLE_KEY`  
     (legacy `service_role` JWT also works; prefer the new secret key format)

Do **not** use the publishable/`anon` key. Only the FastAPI service talks to Supabase (with the secret key).

## 2. Gemini API key (free tier)

1. Create an API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Set `GEMINI_API_KEY` on the Vercel project (shared across services; only `api` needs it at runtime).
3. Optionally set `GEMINI_CHAT_MODEL` to pin a model. Otherwise the API tries, in order:
   - `gemini-3.5-flash-lite`
   - `gemini-3.1-flash-lite`
   - `gemini-flash-latest`
   - `gemini-3.8-flash`  
   and falls back on 404 / timeout (2.5 models are often unavailable to new users).

## 3. Vercel — import the repo once

In the Vercel dashboard, **Import** this GitHub repository as a **single project**. Leave the Root Directory empty (repo root). Vercel reads [`vercel.json`](vercel.json):

| Service | Root | Framework | Public? |
| --- | --- | --- | --- |
| `web` | `apps/web` | Next.js | Yes — catch-all rewrite |
| `api` | `apps/api` | FastAPI | No — binding only |

### Environment variables (Production + Preview)

Set these on the **project** (not per-service URL wiring):

```
GEMINI_API_KEY=...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
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
- `ALLOWED_ORIGINS` — unused in production (API is not on the public internet).

### `INTERNAL_API_TOKEN` (optional, recommended)

Defense in depth on top of network isolation:

1. Generate a long random secret and set `INTERNAL_API_TOKEN` on the project.
2. The Next.js BFF sends it as `X-Internal-Api-Token` on every upstream call.
3. When the env is set, FastAPI rejects requests that omit or mismatch the header.
4. When unset (local pytest / casual demos), the check is skipped.

## 4. Smoke check

```bash
# Public surface is web only — health via BFF
curl https://YOUR_PROJECT.vercel.app/api/health

# FastAPI must NOT be reachable publicly (no rewrite targets api)
# Internal /docs stays available only through the binding / vercel dev.
```

Open `https://YOUR_PROJECT.vercel.app` → Resume → Agent.

## 5. What not to do

- Do **not** enable Vercel’s one-click Supabase integration (env names / keys differ from what the API expects).
- Do **not** commit `.env` files — only `.env.example`.
- Do **not** put `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, or `INTERNAL_API_TOKEN` in client bundles (`NEXT_PUBLIC_*`).
- Do **not** add a top-level rewrite to `api` — that would make FastAPI public and defeat the BFF.

## Local development

### Preferred — `vercel dev` (bindings)

From the repo root (requires Vercel CLI):

```bash
vercel dev
# or fully local without cloud auth:
vercel dev -L
```

This starts both services and injects `API_URL` into `web` from the binding.

### Fallback — two processes (no Vercel CLI)

```bash
# Terminal 1 — API
cd apps/api && uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Web (BFF defaults API_URL to http://127.0.0.1:8000 in development)
cd apps/web
cp .env.example .env.local   # API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

E2E orchestration (`npm run test:e2e`) starts both with `AGENT_MOCK=1` and sets `API_URL` for the Next.js process so Cucumber/Playwright exercise the BFF end-to-end.

## Local ↔ prod parity

| Concern | Local | Prod |
| --- | --- | --- |
| Ingress | `web` on :3000; `api` on :8000 | Only `web` public; `api` via binding |
| `API_URL` | Binding (`vercel dev`) or `http://127.0.0.1:8000` | Service binding (auto) |
| Supabase | Optional — in-memory if unset | Required |
| Gemini | Optional — heuristic / `AGENT_MOCK` | Required for LLM planning |
| `INTERNAL_API_TOKEN` | Optional | Recommended |
| CORS | Harmless localhost default | Not needed |
