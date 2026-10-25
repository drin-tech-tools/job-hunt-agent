# Job Hunt Agent — API

Internal FastAPI service (Vercel Services). Not publicly routed — called only from the Next.js BFF via the `API_URL` binding. See the root [README](../../README.md) Backend Architecture section and [DEPLOYMENT.md](../../DEPLOYMENT.md).

```bash
cp .env.example .env
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q
```

Optional: set `INTERNAL_API_TOKEN` to require `X-Internal-Api-Token` on every request.
