"""Scripted AGENT_MOCK agent runs — no Gemini, no live job boards."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from app.agent.fixtures import (
    FIXTURE_FITS,
    FIXTURE_JOBS,
    MOCK_MARKER_MAX_STEPS,
    MOCK_MARKER_SOURCE_FAILURE,
    MOCK_MARKER_TIMEOUT,
    fixture_cover_letter,
    scored_fixture_jobs,
)
from app.config import Settings
from app.models.schemas import (
    AgentRunRequest,
    AgentRunSummary,
    ScoredJob,
    StepTrace,
)
from app.services.supabase_client import SupabaseService


def _detect_scenario(query: str) -> str:
    q = (query or "").lower()
    if MOCK_MARKER_MAX_STEPS.lower() in q:
        return "max_steps"
    if MOCK_MARKER_SOURCE_FAILURE.lower() in q:
        return "source_failure"
    if MOCK_MARKER_TIMEOUT.lower() in q:
        return "timeout"
    return "happy"


async def run_mock_events(
    req: AgentRunRequest,
    *,
    settings: Settings,
    db: SupabaseService,
    user_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield the same SSE event shapes as AgentRunner.run_events."""
    started = time.perf_counter()
    steps: list[StepTrace] = []
    scenario = _detect_scenario(req.query)

    run_row = db.create_agent_run(
        {
            "query": req.query,
            "resume_id": req.resume_id,
            "user_id": user_id,
            "status": "running",
            "steps": [],
            "result": {},
        }
    )
    run_id = run_row["id"]
    yield {"event": "run_started", "data": {"run_id": run_id}}

    # Tiny delay so the UI can show a live "Running…" state in E2E.
    await asyncio.sleep(0.05)

    if scenario == "timeout":
        step = StepTrace(
            step=1,
            thought_summary="Starting job search…",
            tool="search_jobs",
            args={"query": req.query, "geo": req.location},
            result_summary="waiting on upstream",
            ms=1,
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}
        await asyncio.sleep(0.05)
        message = (
            "Overall agent timeout reached. "
            "The run stopped gracefully — try again or narrow your search."
        )
        summary = AgentRunSummary(
            run_id=run_id,
            status="timeout",
            message=message,
            steps=steps,
            jobs=[],
            model_used="mock-agent",
        )
        db.update_agent_run(
            run_id,
            {
                "status": "timeout",
                "steps": [s.model_dump() for s in steps],
                "result": summary.model_dump(mode="json"),
                "model_used": "mock-agent",
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        yield {"event": "final", "data": summary.model_dump(mode="json")}
        return

    if scenario == "source_failure":
        step = StepTrace(
            step=1,
            thought_summary="Searching Himalayas + Jobicy for matching roles",
            tool="search_jobs",
            args={"query": req.query, "geo": req.location, "limit": req.max_jobs},
            result_summary="0 jobs (sources unavailable)",
            ms=12,
            error="Job sources temporarily unavailable",
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}
        message = (
            "Job sources are temporarily unavailable. "
            "No roles were returned — please try again shortly."
        )
        summary = AgentRunSummary(
            run_id=run_id,
            status="error",
            message=message,
            steps=steps,
            jobs=[],
            model_used="mock-agent",
        )
        db.update_agent_run(
            run_id,
            {
                "status": "error",
                "steps": [s.model_dump() for s in steps],
                "result": summary.model_dump(mode="json"),
                "model_used": "mock-agent",
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        yield {"event": "final", "data": summary.model_dump(mode="json")}
        return

    if scenario == "max_steps":
        max_steps = settings.agent_max_steps
        for i in range(1, max_steps + 1):
            tool = "search_jobs" if i == 1 else f"noop_probe_{i}"
            step = StepTrace(
                step=i,
                thought_summary=f"Mock planning step {i}/{max_steps}",
                tool=tool if i < max_steps else "search_jobs",
                args={"query": req.query, "step": i},
                result_summary=f"mock step {i}",
                ms=2,
            )
            steps.append(step)
            yield {"event": "step", "data": step.model_dump()}
            await asyncio.sleep(0.01)
        message = f"Max steps reached ({max_steps}). Agent stopped by guardrail."
        summary = AgentRunSummary(
            run_id=run_id,
            status="ok",
            message=message,
            steps=steps,
            jobs=[],
            model_used="mock-agent",
        )
        db.update_agent_run(
            run_id,
            {
                "status": "ok",
                "steps": [s.model_dump() for s in steps],
                "result": summary.model_dump(mode="json"),
                "model_used": "mock-agent",
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        yield {"event": "final", "data": summary.model_dump(mode="json")}
        return

    # --- Happy path: scripted tool-call sequence + fixture LLM outputs ---
    search_args = {
        "query": " ".join(req.tags) or "AI engineer",
        "geo": req.location,
        "limit": req.max_jobs,
    }
    step = StepTrace(
        step=1,
        thought_summary="Searching Himalayas + Jobicy for matching roles",
        tool="search_jobs",
        args=search_args,
        result_summary=f"{len(FIXTURE_JOBS)} jobs (mock fixtures)",
        ms=8,
    )
    steps.append(step)
    yield {"event": "step", "data": step.model_dump()}
    await asyncio.sleep(0.03)

    scored = scored_fixture_jobs(req.max_jobs)
    collected: dict[str, ScoredJob] = {sj.job.id: sj for sj in scored}
    step_n = 2

    for sj in scored:
        if step_n > settings.agent_max_steps:
            break
        fit = FIXTURE_FITS[sj.job.id]
        step = StepTrace(
            step=step_n,
            thought_summary=f"Scoring fit for {sj.job.title}",
            tool="score_fit",
            args={"job_id": sj.job.id, "title": sj.job.title},
            result_summary=f"score={fit.score}",
            ms=3,
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}
        step_n += 1
        await asyncio.sleep(0.02)

        if step_n > settings.agent_max_steps:
            break
        draft = fixture_cover_letter(sj.job, fit)
        sj.cover_letter = draft
        step = StepTrace(
            step=step_n,
            thought_summary=f"Drafting cover letter for {sj.job.company}",
            tool="draft_cover_letter",
            args={"job_id": sj.job.id},
            result_summary=f"subject={draft.subject}",
            ms=4,
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}
        step_n += 1
        await asyncio.sleep(0.02)

        if fit.score >= 70 and step_n <= settings.agent_max_steps:
            save_args = {
                "job_id": sj.job.id,
                "title": sj.job.title,
                "company": sj.job.company,
                "apply_url": sj.job.apply_url,
                "source": sj.job.source,
                "status": "saved",
                "score": fit.score,
                "cover_letter": draft.body,
            }
            db.create_tracker(save_args)
            step = StepTrace(
                step=step_n,
                thought_summary="Saving strong fit to tracker",
                tool="save_to_tracker",
                args=save_args,
                result_summary="saved",
                ms=2,
            )
            steps.append(step)
            yield {"event": "step", "data": step.model_dump()}
            step_n += 1
            await asyncio.sleep(0.02)

        # Only auto-save the top fit in happy path to keep step count modest
        break

    jobs = list(collected.values())
    jobs.sort(key=lambda s: (s.fit.score if s.fit else 0), reverse=True)
    jobs = jobs[: req.max_jobs]

    final_thought = (
        f"Found {len(jobs)} scored roles from Himalayas and Jobicy "
        f"for location={req.location or 'any'}."
    )
    if step_n <= settings.agent_max_steps:
        step = StepTrace(
            step=step_n,
            thought_summary=final_thought,
            tool=None,
            args={},
            result_summary="final response",
            ms=1,
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}

    summary = AgentRunSummary(
        run_id=run_id,
        status="ok",
        message=final_thought + " (AGENT_MOCK=1)",
        steps=steps,
        jobs=jobs,
        model_used="mock-agent",
    )
    db.update_agent_run(
        run_id,
        {
            "status": "ok",
            "steps": [s.model_dump() for s in steps],
            "result": summary.model_dump(mode="json"),
            "model_used": "mock-agent",
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
    )
    yield {"event": "final", "data": summary.model_dump(mode="json")}
