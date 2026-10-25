"""Agent loop tests with mocked Gemini + HTTP."""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

from app.agent.loop import AgentRunner
from app.config import get_settings
from app.models.schemas import AgentRunRequest
from app.services.supabase_client import reset_db_for_tests
from tests.conftest import HIMALAYAS_SAMPLE, JOBICY_SAMPLE, RESUME_TEXT


def _mock_http(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://himalayas\.app/jobs/api.*"),
        json=HIMALAYAS_SAMPLE,
    )
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://jobicy\.com/api/v2/remote-jobs.*"),
        json=JOBICY_SAMPLE,
    )


def _mock_gemini_sequence(calls_then_text: list[Any]) -> MagicMock:
    client = MagicMock()

    def _make_fc_response(name: str, args: dict[str, Any], text: str = "") -> MagicMock:
        part_text = MagicMock()
        part_text.text = text
        part_text.function_call = None

        fc = MagicMock()
        fc.name = name
        fc.args = args
        part_fc = MagicMock()
        part_fc.text = None
        part_fc.function_call = fc

        content = MagicMock()
        content.parts = [part_text, part_fc] if text else [part_fc]
        cand = MagicMock()
        cand.content = content
        resp = MagicMock()
        resp.candidates = [cand]
        resp.text = text
        return resp

    def _make_text_response(text: str) -> MagicMock:
        part = MagicMock()
        part.text = text
        part.function_call = None
        content = MagicMock()
        content.parts = [part]
        cand = MagicMock()
        cand.content = content
        resp = MagicMock()
        resp.candidates = [cand]
        resp.text = text
        return resp

    responses = []
    for item in calls_then_text:
        if item.get("type") == "call":
            responses.append(
                _make_fc_response(item["name"], item["args"], item.get("thought", ""))
            )
        else:
            responses.append(_make_text_response(item.get("text", "Done.")))

    client.models.generate_content.side_effect = responses
    return client


@pytest.mark.asyncio
async def test_heuristic_agent_run(httpx_mock: HTTPXMock) -> None:
    _mock_http(httpx_mock)
    reset_db_for_tests()
    get_settings.cache_clear()
    runner = AgentRunner()
    req = AgentRunRequest(
        resume_text=RESUME_TEXT,
        query="Find AI roles",
        max_jobs=5,
        tags=["ai"],
        location="philippines",
    )
    events = []
    async for ev in runner.run_events(req):
        events.append(ev)

    kinds = [e["event"] for e in events]
    assert "run_started" in kinds
    assert "step" in kinds
    assert "final" in kinds
    final = next(e for e in events if e["event"] == "final")
    assert final["data"]["status"] == "ok"
    assert isinstance(final["data"]["steps"], list)
    assert len(final["data"]["steps"]) >= 1


@pytest.mark.asyncio
async def test_gemini_function_calling_loop(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    reset_db_for_tests()
    _mock_http(httpx_mock)

    mock_client = _mock_gemini_sequence(
        [
            {
                "type": "call",
                "name": "search_jobs",
                "args": {"query": "AI engineer", "geo": "philippines", "limit": 12},
                "thought": "Searching boards",
            },
            {
                "type": "call",
                "name": "score_fit",
                "args": {
                    "resume_text": RESUME_TEXT,
                    "job": {
                        "id": "x",
                        "title": "Senior ML Engineer",
                        "company": "Acme AI",
                        "apply_url": "https://himalayas.app/companies/acme/jobs/senior-ml",
                        "source": "Himalayas",
                        "description": "Python FastAPI PyTorch RAG",
                        "tags": ["Python", "AI"],
                    },
                },
            },
            {"type": "text", "text": "Here are your top matches."},
        ]
    )

    runner = AgentRunner(gemini_client=mock_client)
    req = AgentRunRequest(resume_text=RESUME_TEXT, max_jobs=5)
    events = []
    async for ev in runner.run_events(req):
        events.append(ev)

    assert any(e["event"] == "step" and e["data"].get("tool") == "search_jobs" for e in events)
    assert any(e["event"] == "final" for e in events)
    assert mock_client.models.generate_content.called


def test_agent_run_sse_endpoint(client, httpx_mock: HTTPXMock) -> None:
    _mock_http(httpx_mock)
    with client.stream(
        "POST",
        "/agent/run",
        json={
            "resume_text": RESUME_TEXT,
            "query": "Find roles",
            "max_jobs": 5,
            "tags": ["ai"],
        },
    ) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    assert "run_started" in body or "final" in body or "step" in body
