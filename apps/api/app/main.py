"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routes import agent, health, resumes, tracker

settings = get_settings()

app = FastAPI(
    title="Job Hunt Agent API",
    version=__version__,
    description="AI job-hunt agent — Gemini function calling + Himalayas/Jobicy",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(resumes.router)
app.include_router(tracker.router)
app.include_router(agent.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "job-hunt-agent-api",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
