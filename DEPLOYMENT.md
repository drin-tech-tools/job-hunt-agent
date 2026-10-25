# Deployment (all free tiers)

Deploy this monorepo as **two Vercel Hobby projects** from the same public GitHub repository. Skip Vercel’s Supabase marketplace integration — configure Supabase manually.

> **Hobby requirement:** the GitHub repository must be **public** for org/team Hobby deploys from a connected repo.

## 1. Supabase (free project)

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** → New query → paste and run [`supabase/migrations/001_init.sql`](supabase/migrations/001_init.sql).
3. Open **Project Settings → API Keys**.
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **Secret key** (`sb_secret_...`) → `SUPABASE_SERVICE_ROLE_KEY`  
     (legacy `service_role` JWT also works; prefer the new secret key format)

Do **not** use the publishable/`anon` key in the API. The FastAPI app talks to Supabase with the secret key only.

## 2. Gemini API key (free tier)

1. Create an API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Set `GEMINI_API_KEY` on the API project.
3. Optionally set `GEMINI_CHAT_MODEL` to pin a model. Otherwise the API tries, in order:
   - `gemini-3.5-flash-lite`
   - `gemini-3.1-flash-lite`
   - `gemini-flash-latest`
   - `gemini-3.8-flash`  
   and falls back on 404 / timeout (2.5 models are often unavailable to new users).

## 3. Vercel — create two projects from this repo

In the Vercel dashboard, import the **same** GitHub repository twice:

### Project A — API

| Setting | Value |
| --- | --- |
| Root Directory | `apps/api` |
| Framework | Other (uses `vercel.json` + `@vercel/python`) |
| Install / Build | defaults from `vercel.json` |

**Environment variables (Production + Preview):**

```
GEMINI_API_KEY=...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
ALLOWED_ORIGINS=https://YOUR_WEB_PROJECT.vercel.app
```

Optional:

```
GEMINI_CHAT_MODEL=
JSEARCH_API_KEY=
```

Deploy, then copy the API URL (e.g. `https://job-hunt-agent-api.vercel.app`).

### Project B — Web

| Setting | Value |
| --- | --- |
| Root Directory | `apps/web` |
| Framework | Next.js |

**Environment variables:**

```
NEXT_PUBLIC_API_URL=https://YOUR_API_PROJECT.vercel.app
```

Deploy, then copy the Web URL.

### Wire CORS + API URL

1. Set API `ALLOWED_ORIGINS` to the **web** origin (comma-separated if you have preview + prod; no trailing slash).
2. Set Web `NEXT_PUBLIC_API_URL` to the **api** origin (no trailing slash).
3. Redeploy both so env changes apply.

## 4. Smoke check

```bash
curl https://YOUR_API_PROJECT.vercel.app/health
# open https://YOUR_WEB_PROJECT.vercel.app → Resume → Agent
```

## 5. What not to do

- Do **not** enable Vercel’s one-click Supabase integration for this project (env names / keys differ from what the API expects).
- Do **not** commit `.env` files — only `.env.example`.
- Do **not** put `SUPABASE_SERVICE_ROLE_KEY` or `GEMINI_API_KEY` in the Next.js project.

## Local ↔ prod parity

| Concern | Local | Prod |
| --- | --- | --- |
| Supabase | Optional — in-memory store if unset | Required |
| Gemini | Optional — heuristic tool loop | Required for LLM planning |
| CORS | `http://localhost:3000` | Web Vercel URL |
