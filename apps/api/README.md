# Job Hunt Agent — API

FastAPI backend for Vercel Python. See the root [README](../../README.md) and [DEPLOYMENT.md](../../DEPLOYMENT.md).

```bash
cp .env.example .env
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q
```
