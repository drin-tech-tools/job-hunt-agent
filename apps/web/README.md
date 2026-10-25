# Job Hunt Agent — Web

Next.js App Router UI + same-origin BFF under `/api/*`. Route Handlers proxy allowlisted calls to the internal FastAPI service using `API_URL` (Vercel binding, or `http://127.0.0.1:8000` in local development). See the root [README](../../README.md) and [DEPLOYMENT.md](../../DEPLOYMENT.md).

```bash
cp .env.example .env.local
# API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Do not set `NEXT_PUBLIC_API_URL` — the browser only calls `/api/*`.
