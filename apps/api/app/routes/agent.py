"""Agent run endpoint with SSE streaming (AAL2 + run_agent permission)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.agent.loop import AgentRunner
from app.auth.deps import require_permission
from app.auth.models import CurrentUser
from app.auth.permissions import Permission
from app.models.schemas import AgentRunRequest

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run")
async def run_agent(
    body: AgentRunRequest,
    user: CurrentUser = Depends(require_permission(Permission.run_agent)),
) -> EventSourceResponse:
    """Stream SSE events: run_started, step, final, error."""

    runner = AgentRunner()

    async def event_generator() -> Any:
        async for event in runner.run_events(body, user_id=user.id):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"], default=str),
            }

    return EventSourceResponse(event_generator())
