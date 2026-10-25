"""Agent run endpoint with SSE streaming."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agent.loop import AgentRunner
from app.models.schemas import AgentRunRequest

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run")
async def run_agent(body: AgentRunRequest) -> EventSourceResponse:
    """Stream SSE events: run_started, step, final, error."""

    runner = AgentRunner()

    async def event_generator() -> Any:
        async for event in runner.run_events(body):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"], default=str),
            }

    return EventSourceResponse(event_generator())
