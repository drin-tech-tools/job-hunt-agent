"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.services.supabase_client import reset_db_for_tests


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_db_for_tests()
    yield
    get_settings.cache_clear()
    reset_db_for_tests()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


HIMALAYAS_SAMPLE = {
    "jobs": [
        {
            "title": "Senior ML Engineer",
            "companyName": "Acme AI",
            "applicationLink": "https://himalayas.app/companies/acme/jobs/senior-ml",
            "description": "Build LLM agents with Python, FastAPI, PyTorch, and RAG.",
            "categories": ["AI", "Python", "Machine Learning"],
            "locationRestrictions": ["Worldwide"],
            "pubDate": "2026-01-01",
        },
        {
            "title": "Frontend Designer",
            "companyName": "Pretty Pixels",
            "applicationLink": "https://himalayas.app/companies/pretty/jobs/designer",
            "description": "Figma and illustration only.",
            "categories": ["Design"],
            "pubDate": "2026-01-02",
        },
    ]
}

JOBICY_SAMPLE = {
    "jobs": [
        {
            "id": 1,
            "jobTitle": "AI Platform Engineer",
            "companyName": "Orbital Labs",
            "url": "https://jobicy.com/jobs/ai-platform-engineer",
            "jobDescription": "Python, Kubernetes, LLMOps, FastAPI microservices.",
            "jobIndustry": "AI, Software",
            "jobGeo": "Anywhere",
            "pubDate": "2026-01-03",
        },
        {
            "id": 2,
            "jobTitle": "AI Platform Engineer",
            "companyName": "Orbital Labs",
            "url": "https://jobicy.com/jobs/ai-platform-engineer/",
            "jobDescription": "Duplicate by URL trailing slash.",
            "jobIndustry": "AI",
            "jobGeo": "Anywhere",
        },
    ]
}

RESUME_TEXT = """
Jane Doe
AI Engineer

Skills: Python, FastAPI, PyTorch, LLM, RAG, Docker, Kubernetes, SQL, Postgres, TypeScript
Experience building production RAG agents and ML platforms.
"""
