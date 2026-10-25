"""Agent loop using Google Gemini native function calling with guardrails."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from app.config import Settings, get_settings
from app.models.schemas import (
    AgentRunRequest,
    AgentRunSummary,
    FitScore,
    JobPosting,
    ScoredJob,
    StepTrace,
)
from app.services.supabase_client import SupabaseService, get_db
from app.tools.registry import TOOL_DECLARATIONS, execute_tool, get_tool_handlers
from app.tools.scoring import draft_cover_letter, score_fit

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI job-hunt agent helping a candidate find and evaluate remote roles.

Rules:
- Use tools to search jobs, score fit, draft cover letters, and save promising roles to the tracker.
- Always preserve job source attribution (Himalayas or Jobicy) and the original apply URL.
- Prefer high-fit roles. Score the most relevant jobs (up to the user's max_jobs).
- Keep tool args compact. Do not invent jobs — only use tool results.
- When done, write a short final summary for the candidate (no more tool calls).
"""


def _extract_function_calls(response: Any) -> list[tuple[str, dict[str, Any], str | None]]:
    """Return list of (name, args, thought_summary) from a Gemini response."""
    calls: list[tuple[str, dict[str, Any], str | None]] = []
    thought = ""
    try:
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", None) or []:
                text = getattr(part, "text", None)
                if text:
                    thought = (thought + " " + text).strip()[:500]
                fc = getattr(part, "function_call", None)
                if fc:
                    name = getattr(fc, "name", None) or ""
                    raw_args = getattr(fc, "args", None) or {}
                    if hasattr(raw_args, "items"):
                        args = dict(raw_args)
                    elif isinstance(raw_args, dict):
                        args = raw_args
                    else:
                        args = {}
                    # Convert nested protobuf maps if needed
                    args = json.loads(json.dumps(args, default=str))
                    calls.append((name, args, thought or None))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse function calls: %s", exc)
    return calls


def _extract_text(response: Any) -> str:
    try:
        text = getattr(response, "text", None)
        if text:
            return str(text)
    except Exception:  # noqa: BLE001
        pass
    chunks: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                chunks.append(str(t))
    return "\n".join(chunks).strip()


def _build_genai_tools() -> list[Any]:
    from google.genai import types

    decls = []
    for d in TOOL_DECLARATIONS:
        decls.append(
            types.FunctionDeclaration(
                name=d["name"],
                description=d.get("description"),
                parameters=d.get("parameters"),
            )
        )
    return [types.Tool(function_declarations=decls)]


def _thinking_config() -> Any | None:
    """Low/no thinking where supported by the SDK."""
    try:
        from google.genai import types

        # thinking_budget=0 disables extended thinking when the model supports it
        return types.ThinkingConfig(thinking_budget=0)
    except Exception:  # noqa: BLE001
        return None


class AgentRunner:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        db: SupabaseService | None = None,
        gemini_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db or get_db()
        self._client = gemini_client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from google import genai

        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    async def _generate(self, model: str, contents: list[Any], config: Any) -> Any:
        client = self._get_client()

        def _call() -> Any:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

        return await asyncio.to_thread(_call)

    async def _generate_with_fallback(
        self,
        contents: list[Any],
        config: Any,
    ) -> tuple[Any, str]:
        errors: list[str] = []
        for model in self.settings.chat_models:
            try:
                resp = await asyncio.wait_for(
                    self._generate(model, contents, config),
                    timeout=min(45.0, self.settings.agent_overall_timeout_s),
                )
                return resp, model
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).lower()
                errors.append(f"{model}: {exc}")
                # Fall through on 404 / not found / timeout / unavailable
                if any(
                    s in msg
                    for s in (
                        "404", "not found", "timeout",
                        "unavailable", "not supported", "invalid",
                    )
                ):
                    logger.warning("Model %s failed, trying next: %s", model, exc)
                    continue
                logger.warning("Model %s error (still falling back): %s", model, exc)
                continue
        raise RuntimeError("All Gemini models failed: " + " | ".join(errors))

    async def run_events(
        self,
        req: AgentRunRequest,
        *,
        user_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield SSE-friendly event dicts: step | final | error."""
        started = time.perf_counter()
        steps: list[StepTrace] = []
        collected_jobs: dict[str, ScoredJob] = {}
        model_used: str | None = None
        status = "ok"
        message = ""

        resume_text = req.resume_text or ""
        if req.resume_id and not resume_text:
            row = self.db.get_resume(req.resume_id)
            if row:
                resume_text = row.get("content") or ""

        run_row = self.db.create_agent_run(
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

        handlers = get_tool_handlers(
            settings=self.settings,
            db=self.db,
            resume_text_default=resume_text,
        )

        # Full-stack mock mode for BDD / CI — fixture jobs + scripted tool sequence
        if self.settings.agent_mock and self._client is None:
            from app.agent.mock_runner import run_mock_events

            async for ev in run_mock_events(
                req, settings=self.settings, db=self.db, user_id=user_id
            ):
                yield ev
            return

        # Deterministic bootstrap when no API key (local/tests) — still exercises tools
        if not self.settings.gemini_api_key and self._client is None:
            async for ev in self._heuristic_run(
                req, resume_text, handlers, run_id, started, steps, collected_jobs
            ):
                yield ev
            return

        from google.genai import types

        tools = _build_genai_tools()
        thinking = _thinking_config()
        config_kwargs: dict[str, Any] = {
            "tools": tools,
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.2,
        }
        if thinking is not None:
            config_kwargs["thinking_config"] = thinking
        config = types.GenerateContentConfig(**config_kwargs)

        user_prompt = (
            f"Candidate resume:\n{resume_text[:12000]}\n\n"
            f"Task: {req.query}\n"
            f"Preferences: location/geo={req.location}, tags={req.tags}, max_jobs={req.max_jobs}.\n"
            "1) search_jobs 2) score_fit for the best matches 3) draft_cover_letter for top 1-3 "
            "4) save_to_tracker for strong fits (score>=70) with status=saved. Then summarize."
        )

        contents: list[Any] = [
            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
        ]

        try:
            for step_idx in range(1, self.settings.agent_max_steps + 1):
                elapsed = time.perf_counter() - started
                if elapsed > self.settings.agent_overall_timeout_s:
                    status = "timeout"
                    message = "Overall agent timeout reached"
                    break

                try:
                    response, model_used = await self._generate_with_fallback(contents, config)
                except Exception as exc:  # noqa: BLE001
                    status = "error"
                    message = str(exc)
                    yield {
                        "event": "error",
                        "data": {"message": message, "run_id": run_id},
                    }
                    break

                calls = _extract_function_calls(response)
                if not calls:
                    message = _extract_text(response) or "Done."
                    step = StepTrace(
                        step=step_idx,
                        thought_summary=message[:500],
                        tool=None,
                        args={},
                        result_summary="final response",
                        ms=0,
                    )
                    steps.append(step)
                    yield {"event": "step", "data": step.model_dump()}
                    break

                # Append model turn
                model_content = response.candidates[0].content
                contents.append(model_content)

                fn_response_parts: list[Any] = []
                for name, args, thought in calls:
                    # Inject resume_text when missing for scoring tools
                    if name in ("score_fit", "draft_cover_letter") and "resume_text" not in args:
                        args = {**args, "resume_text": resume_text}

                    t0 = time.perf_counter()
                    result, summary, ms = await execute_tool(
                        name, args, handlers=handlers, settings=self.settings
                    )
                    _ = t0
                    step = StepTrace(
                        step=step_idx,
                        thought_summary=(thought or f"Calling {name}")[:500],
                        tool=name,
                        args=args,
                        result_summary=summary,
                        ms=ms,
                        error=result.get("error") if isinstance(result, dict) else None,
                    )
                    steps.append(step)
                    yield {"event": "step", "data": step.model_dump()}

                    self._ingest_tool_result(name, result, collected_jobs, resume_text)

                    fn_response_parts.append(
                        types.Part.from_function_response(
                            name=name,
                            response={"result": result},
                        )
                    )

                contents.append(types.Content(role="user", parts=fn_response_parts))

                if len(steps) >= self.settings.agent_max_steps:
                    message = message or "Max steps reached."
                    break
            else:
                message = message or "Max steps reached."

        except Exception as exc:  # noqa: BLE001
            status = "error"
            message = str(exc)
            yield {"event": "error", "data": {"message": message, "run_id": run_id}}

        jobs = list(collected_jobs.values())
        jobs.sort(key=lambda s: (s.fit.score if s.fit else 0), reverse=True)
        jobs = jobs[: req.max_jobs]

        if status not in ("ok", "error", "timeout"):
            status = "ok"
        summary = AgentRunSummary(
            run_id=run_id,
            status=status,  # type: ignore[arg-type]
            message=message or f"Found {len(jobs)} scored roles.",
            steps=steps,
            jobs=jobs,
            model_used=model_used,
        )

        self.db.update_agent_run(
            run_id,
            {
                "status": summary.status,
                "steps": [s.model_dump() for s in steps],
                "result": summary.model_dump(mode="json"),
                "model_used": model_used,
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        yield {"event": "final", "data": summary.model_dump(mode="json")}

    def _ingest_tool_result(
        self,
        name: str,
        result: Any,
        collected: dict[str, ScoredJob],
        resume_text: str,
    ) -> None:
        if name == "search_jobs" and isinstance(result, list):
            for raw in result:
                try:
                    job = JobPosting.model_validate(raw)
                except Exception:  # noqa: BLE001
                    continue
                if job.id not in collected:
                    collected[job.id] = ScoredJob(job=job)
        elif name == "fetch_posting" and isinstance(result, dict) and "id" in result:
            try:
                job = JobPosting.model_validate(result)
                collected.setdefault(job.id, ScoredJob(job=job))
            except Exception:  # noqa: BLE001
                pass
        elif name == "score_fit" and isinstance(result, dict) and "score" in result:
            # Attach to most recent unscored or matching — best effort via matched skills alone
            try:
                fit = FitScore.model_validate(result)
            except Exception:  # noqa: BLE001
                return
            # If only one job, attach; else attach to first without fit
            for sj in collected.values():
                if sj.fit is None:
                    sj.fit = fit
                    break
        elif name == "draft_cover_letter" and isinstance(result, dict) and "body" in result:
            from app.models.schemas import CoverLetterDraft

            try:
                draft = CoverLetterDraft.model_validate(result)
            except Exception:  # noqa: BLE001
                return
            for sj in collected.values():
                if draft.job_id and sj.job.id == draft.job_id:
                    sj.cover_letter = draft
                    return
            for sj in collected.values():
                if sj.cover_letter is None:
                    sj.cover_letter = draft
                    return
        _ = resume_text

    async def _heuristic_run(
        self,
        req: AgentRunRequest,
        resume_text: str,
        handlers: dict[str, Any],
        run_id: str,
        started: float,
        steps: list[StepTrace],
        collected_jobs: dict[str, ScoredJob],
    ) -> AsyncIterator[dict[str, Any]]:
        """Offline/demo path when GEMINI_API_KEY is missing — still produces a full trace."""
        tag = req.tags[0] if req.tags else None
        args = {
            "query": " ".join(req.tags) or "AI engineer",
            "geo": req.location,
            "tag": tag,
            "limit": req.max_jobs,
        }
        result, summary, ms = await execute_tool(
            "search_jobs", args, handlers=handlers, settings=self.settings
        )
        step = StepTrace(
            step=1,
            thought_summary="Searching Himalayas + Jobicy for matching roles",
            tool="search_jobs",
            args=args,
            result_summary=summary,
            ms=ms,
        )
        steps.append(step)
        yield {"event": "step", "data": step.model_dump()}
        self._ingest_tool_result("search_jobs", result, collected_jobs, resume_text)

        step_n = 2
        for sj in list(collected_jobs.values())[: req.max_jobs]:
            if time.perf_counter() - started > self.settings.agent_overall_timeout_s:
                break
            if step_n > self.settings.agent_max_steps:
                break
            fit = score_fit(resume_text or "python fastapi llm", sj.job)
            sj.fit = fit
            step = StepTrace(
                step=step_n,
                thought_summary=f"Scoring fit for {sj.job.title}",
                tool="score_fit",
                args={"job_id": sj.job.id, "title": sj.job.title},
                result_summary=f"score={fit.score}",
                ms=1,
            )
            steps.append(step)
            yield {"event": "step", "data": step.model_dump()}
            step_n += 1

            if fit.score >= 70 and step_n <= self.settings.agent_max_steps:
                draft = draft_cover_letter(resume_text or "Candidate", sj.job, fit)
                sj.cover_letter = draft
                step = StepTrace(
                    step=step_n,
                    thought_summary=f"Drafting cover letter for {sj.job.company}",
                    tool="draft_cover_letter",
                    args={"job_id": sj.job.id},
                    result_summary=f"subject={draft.subject}",
                    ms=1,
                )
                steps.append(step)
                yield {"event": "step", "data": step.model_dump()}
                step_n += 1

                if step_n <= self.settings.agent_max_steps:
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
                    result, summary, ms = await execute_tool(
                        "save_to_tracker", save_args, handlers=handlers, settings=self.settings
                    )
                    step = StepTrace(
                        step=step_n,
                        thought_summary="Saving strong fit to tracker",
                        tool="save_to_tracker",
                        args=save_args,
                        result_summary=summary,
                        ms=ms,
                    )
                    steps.append(step)
                    yield {"event": "step", "data": step.model_dump()}
                    step_n += 1

        jobs = sorted(
            collected_jobs.values(),
            key=lambda s: (s.fit.score if s.fit else 0),
            reverse=True,
        )[: req.max_jobs]
        summary_obj = AgentRunSummary(
            run_id=run_id,
            status="ok",
            message=(
                f"Heuristic run complete — {len(jobs)} roles "
                "(set GEMINI_API_KEY for LLM planning)."
            ),
            steps=steps,
            jobs=jobs,
            model_used=None,
        )
        self.db.update_agent_run(
            run_id,
            {
                "status": "ok",
                "steps": [s.model_dump() for s in steps],
                "result": summary_obj.model_dump(mode="json"),
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        yield {"event": "final", "data": summary_obj.model_dump(mode="json")}


async def run_agent_events(req: AgentRunRequest, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
    runner = AgentRunner(**kwargs)
    async for event in runner.run_events(req):
        yield event
