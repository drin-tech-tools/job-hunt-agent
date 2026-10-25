"""AGENT_MOCK mode — deterministic fixture runs for BDD/CI."""

from __future__ import annotations

import pytest

from app.agent.loop import AgentRunner
from app.config import get_settings
from app.models.schemas import AgentRunRequest
from tests.conftest import RESUME_TEXT


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MOCK", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


async def _collect(req: AgentRunRequest) -> list[dict]:
    runner = AgentRunner()
    events = []
    async for ev in runner.run_events(req):
        events.append(ev)
    return events


@pytest.mark.asyncio
async def test_mock_happy_path_returns_fixture_jobs(mock_settings):
    assert mock_settings.agent_mock is True
    events = await _collect(
        AgentRunRequest(
            resume_text=RESUME_TEXT,
            query="Find remote AI engineer roles in philippines",
            max_jobs=3,
            location="philippines",
            tags=["ai", "python"],
        )
    )
    kinds = [e["event"] for e in events]
    assert kinds[0] == "run_started"
    assert "step" in kinds
    assert kinds[-1] == "final"
    final = events[-1]["data"]
    assert final["status"] == "ok"
    assert final["model_used"] == "mock-agent"
    assert len(final["jobs"]) >= 2
    sources = {j["job"]["source"] for j in final["jobs"]}
    assert "Himalayas" in sources
    assert "Jobicy" in sources
    assert all(j["fit"] and j["fit"]["score"] > 0 for j in final["jobs"])
    assert all(j["job"]["apply_url"].startswith("http") for j in final["jobs"])


@pytest.mark.asyncio
async def test_mock_max_steps_guardrail(mock_settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MAX_STEPS", "3")
    get_settings.cache_clear()
    events = await _collect(
        AgentRunRequest(resume_text=RESUME_TEXT, query="Demo [max_steps] guardrail")
    )
    final = events[-1]["data"]
    assert "Max steps reached" in final["message"]
    assert len(final["steps"]) == 3


@pytest.mark.asyncio
async def test_mock_source_failure_graceful(mock_settings):
    events = await _collect(
        AgentRunRequest(resume_text=RESUME_TEXT, query="Search with [source_failure]")
    )
    final = events[-1]["data"]
    assert final["status"] == "error"
    assert "temporarily unavailable" in final["message"].lower()
    assert final["jobs"] == []


@pytest.mark.asyncio
async def test_mock_timeout_graceful(mock_settings):
    events = await _collect(
        AgentRunRequest(resume_text=RESUME_TEXT, query="Run with [timeout] marker")
    )
    final = events[-1]["data"]
    assert final["status"] == "timeout"
    assert "timeout" in final["message"].lower()
