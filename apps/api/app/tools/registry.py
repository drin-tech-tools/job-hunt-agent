"""Tool declarations (Gemini function calling) and dispatch."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings, get_settings
from app.models.schemas import JobPosting, TrackerStatus
from app.services.supabase_client import SupabaseService, get_db
from app.tools.jobs import fetch_posting, search_jobs
from app.tools.scoring import draft_cover_letter, score_fit

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]


class SearchJobsArgs(BaseModel):
    query: str = Field(default="AI engineer", description="Search keywords")
    geo: str | None = Field(default="philippines", description="Jobicy geo filter")
    tag: str | None = Field(default=None, description="Jobicy tag filter, e.g. python")
    limit: int = Field(default=12, ge=1, le=30)


class FetchPostingArgs(BaseModel):
    url: str | None = None
    job_id: str | None = None


class ScoreFitArgs(BaseModel):
    resume_text: str
    job: dict[str, Any]


class DraftCoverLetterArgs(BaseModel):
    resume_text: str
    job: dict[str, Any]


class SaveToTrackerArgs(BaseModel):
    job_id: str
    title: str
    company: str
    apply_url: str
    source: str
    status: TrackerStatus = TrackerStatus.saved
    score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    cover_letter: str | None = None


# OpenAPI-ish declarations for Gemini native function calling
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "search_jobs",
        "description": (
            "Search remote jobs from Himalayas and Jobicy concurrently. "
            "Results include source attribution and original apply URLs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "geo": {
                    "type": "string",
                    "description": "Geo filter for Jobicy (e.g. philippines)",
                },
                "tag": {"type": "string", "description": "Tag filter for Jobicy"},
                "limit": {"type": "integer", "description": "Max jobs to return"},
            },
        },
    },
    {
        "name": "fetch_posting",
        "description": "Fetch a single job posting by apply URL or cached job_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "job_id": {"type": "string"},
            },
        },
    },
    {
        "name": "score_fit",
        "description": (
            "Score resume-to-job fit 0-100 with matched skills and gaps. "
            "Returns structured JSON validated by Pydantic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string"},
                "job": {"type": "object", "description": "JobPosting-shaped object"},
            },
            "required": ["resume_text", "job"],
        },
    },
    {
        "name": "draft_cover_letter",
        "description": "Draft a tailored cover letter for a job posting given the resume.",
        "parameters": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string"},
                "job": {"type": "object"},
            },
            "required": ["resume_text", "job"],
        },
    },
    {
        "name": "save_to_tracker",
        "description": (
            "Save a job to the application tracker "
            "(saved/applied/interview/offer/rejected)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "title": {"type": "string"},
                "company": {"type": "string"},
                "apply_url": {"type": "string"},
                "source": {"type": "string", "enum": ["Himalayas", "Jobicy", "JSearch"]},
                "status": {
                    "type": "string",
                    "enum": ["saved", "applied", "interview", "offer", "rejected"],
                },
                "score": {"type": "integer"},
                "notes": {"type": "string"},
                "cover_letter": {"type": "string"},
            },
            "required": ["job_id", "title", "company", "apply_url", "source"],
        },
    },
]


def _summarize_result(name: str, result: Any) -> str:
    try:
        if name == "search_jobs" and isinstance(result, list):
            return f"{len(result)} jobs: " + ", ".join(
                f"{j.get('title', '?')} @ {j.get('company', '?')} (via {j.get('source')})"
                for j in result[:5]
            )
        if name == "score_fit" and isinstance(result, dict):
            return (
                f"score={result.get('score')} "
                f"matched={result.get('matched_skills')} "
                f"gaps={result.get('gaps')}"
            )
        if name == "draft_cover_letter" and isinstance(result, dict):
            return f"subject={result.get('subject')}; body_len={len(result.get('body') or '')}"
        if name == "save_to_tracker" and isinstance(result, dict):
            return f"tracker_id={result.get('id')} status={result.get('status')}"
        if isinstance(result, dict) and "error" in result:
            return f"error: {result['error']}"
        text = json.dumps(result, default=str)
        return text[:400] + ("…" if len(text) > 400 else "")
    except Exception:  # noqa: BLE001
        return str(result)[:400]


async def _with_retries(
    coro_factory: Callable[[], Awaitable[Any]],
    *,
    retries: int,
    timeout_s: float,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(coro_factory(), timeout=timeout_s)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= retries:
                break
            await asyncio.sleep(0.4 * (2**attempt))
    return {"error": str(last_exc) if last_exc else "unknown tool error"}


def get_tool_handlers(
    *,
    settings: Settings | None = None,
    db: SupabaseService | None = None,
    resume_text_default: str = "",
) -> dict[str, ToolHandler]:
    settings = settings or get_settings()
    db = db or get_db()

    async def _search_jobs(**kwargs: Any) -> Any:
        args = SearchJobsArgs.model_validate(kwargs)
        jobs = await search_jobs(
            query=args.query,
            geo=args.geo,
            tag=args.tag,
            limit=args.limit,
            settings=settings,
            db=db,
        )
        return [j.model_dump() for j in jobs]

    async def _fetch_posting(**kwargs: Any) -> Any:
        args = FetchPostingArgs.model_validate(kwargs)
        result = await fetch_posting(
            url=args.url,
            job_id=args.job_id,
            settings=settings,
            db=db,
        )
        if isinstance(result, JobPosting):
            return result.model_dump()
        return result

    async def _score_fit(**kwargs: Any) -> Any:
        args = ScoreFitArgs.model_validate(kwargs)
        resume = args.resume_text or resume_text_default
        fit = score_fit(resume, args.job)
        return fit.model_dump()

    async def _draft_cover_letter(**kwargs: Any) -> Any:
        args = DraftCoverLetterArgs.model_validate(kwargs)
        resume = args.resume_text or resume_text_default
        draft = draft_cover_letter(resume, args.job)
        return draft.model_dump()

    async def _save_to_tracker(**kwargs: Any) -> Any:
        args = SaveToTrackerArgs.model_validate(kwargs)
        row = db.create_tracker(
            {
                "job_id": args.job_id,
                "title": args.title,
                "company": args.company,
                "apply_url": args.apply_url,
                "source": args.source,
                "status": (
                    args.status.value
                    if isinstance(args.status, TrackerStatus)
                    else args.status
                ),
                "score": args.score,
                "notes": args.notes,
                "cover_letter": args.cover_letter,
            }
        )
        return row

    return {
        "search_jobs": _search_jobs,
        "fetch_posting": _fetch_posting,
        "score_fit": _score_fit,
        "draft_cover_letter": _draft_cover_letter,
        "save_to_tracker": _save_to_tracker,
    }


async def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    handlers: dict[str, ToolHandler] | None = None,
    settings: Settings | None = None,
) -> tuple[Any, str, int]:
    """Execute a named tool with timeout/retries. Returns (result, summary, ms)."""
    settings = settings or get_settings()
    handlers = handlers or get_tool_handlers(settings=settings)
    handler = handlers.get(name)
    started = time.perf_counter()
    if not handler:
        result: Any = {"error": f"Unknown tool: {name}"}
        ms = int((time.perf_counter() - started) * 1000)
        return result, _summarize_result(name, result), ms

    async def _run() -> Any:
        try:
            return await handler(**(args or {}))
        except ValidationError as exc:
            return {"error": f"Invalid args for {name}: {exc}"}

    result = await _with_retries(
        _run,
        retries=settings.tool_max_retries,
        timeout_s=settings.tool_timeout_s,
    )
    ms = int((time.perf_counter() - started) * 1000)
    return result, _summarize_result(name, result), ms
