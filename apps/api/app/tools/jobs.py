"""Job board clients: Himalayas + Jobicy (+ optional JSearch stub)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings, get_settings
from app.models.schemas import JobPosting
from app.services.supabase_client import SupabaseService, get_db

logger = logging.getLogger(__name__)

HIMALAYAS_URL = "https://himalayas.app/jobs/api"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "job"


def _job_id(source: str, url: str, title: str, company: str) -> str:
    raw = f"{source}|{url}|{title}|{company}".encode()
    return hashlib.sha1(raw).hexdigest()[:16]  # noqa: S324 — non-crypto id


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    if not u.startswith("http"):
        u = "https://" + u.lstrip("/")
    return u


def _dedupe_key(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    path = (parsed.path or "").rstrip("/")
    return f"{host}{path}"


async def _fetch_himalayas(
    client: httpx.AsyncClient,
    *,
    query: str | None,
    limit: int,
) -> list[JobPosting]:
    params: dict[str, Any] = {"limit": min(limit, 20)}
    if query:
        # Himalayas supports offset/limit; filter client-side by keywords.
        pass
    try:
        resp = await client.get(HIMALAYAS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Himalayas fetch failed: %s", exc)
        return []

    jobs_raw = data.get("jobs") if isinstance(data, dict) else data
    if not isinstance(jobs_raw, list):
        return []

    keywords = [k.lower() for k in re.split(r"[\s,]+", query or "") if k]
    out: list[JobPosting] = []
    for item in jobs_raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("jobTitle") or "").strip()
        company = str(
            item.get("companyName")
            or (item.get("company") or {}).get("name")
            if isinstance(item.get("company"), dict)
            else item.get("company")
            or "Unknown"
        ).strip()
        apply_url = _normalize_url(
            item.get("applicationLink")
            or item.get("guid")
            or item.get("url")
            or item.get("permalink")
        )
        if not title or not apply_url:
            continue
        blob = f"{title} {company} {item.get('description') or ''}".lower()
        if keywords and not any(k in blob for k in keywords):
            # Soft filter — keep if no keywords match but still within limit later
            pass
        tags = item.get("categories") or item.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        location = None
        locs = item.get("locationRestrictions") or item.get("locations") or []
        if isinstance(locs, list) and locs:
            location = ", ".join(str(x) for x in locs[:3])
        elif isinstance(locs, str):
            location = locs

        desc = item.get("description") or item.get("excerpt") or ""
        if isinstance(desc, str) and len(desc) > 4000:
            desc = desc[:4000] + "…"

        out.append(
            JobPosting(
                id=_job_id("Himalayas", apply_url, title, company),
                title=title,
                company=company or "Unknown",
                location=location,
                description=desc or None,
                apply_url=apply_url,
                source="Himalayas",
                salary=None,
                tags=[str(t) for t in tags][:12],
                posted_at=str(item.get("pubDate") or item.get("published_at") or "") or None,
            )
        )
    if keywords:
        scored = []
        for j in out:
            blob = f"{j.title} {j.company} {' '.join(j.tags)} {j.description or ''}".lower()
            hits = sum(1 for k in keywords if k in blob)
            scored.append((hits, j))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = [j for _, j in scored]
    return out[:limit]


async def _fetch_jobicy(
    client: httpx.AsyncClient,
    *,
    query: str | None,
    geo: str | None,
    tag: str | None,
    limit: int,
) -> list[JobPosting]:
    params: dict[str, Any] = {"count": min(limit, 50)}
    if geo:
        params["geo"] = geo
    if tag:
        params["tag"] = tag
    try:
        resp = await client.get(JOBICY_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Jobicy fetch failed: %s", exc)
        return []

    jobs_raw = data.get("jobs") if isinstance(data, dict) else []
    if not isinstance(jobs_raw, list):
        return []

    keywords = [k.lower() for k in re.split(r"[\s,]+", query or "") if k]
    out: list[JobPosting] = []
    for item in jobs_raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("jobTitle") or item.get("title") or "").strip()
        company = str(item.get("companyName") or item.get("company") or "Unknown").strip()
        apply_url = _normalize_url(item.get("url") or item.get("jobUrl") or item.get("applyUrl"))
        if not title or not apply_url:
            continue
        tags = item.get("jobIndustry") or item.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        desc = item.get("jobDescription") or item.get("description") or ""
        if isinstance(desc, str) and len(desc) > 4000:
            desc = desc[:4000] + "…"
        location = item.get("jobGeo") or item.get("location")
        salary = item.get("salaryMin") or item.get("annualSalaryMin")
        salary_str = None
        if salary:
            currency = item.get("salaryCurrency") or "USD"
            salary_str = f"{currency} {salary}+"

        out.append(
            JobPosting(
                id=_job_id("Jobicy", apply_url, title, company),
                title=title,
                company=company or "Unknown",
                location=str(location) if location else None,
                description=desc or None,
                apply_url=apply_url,
                source="Jobicy",
                salary=salary_str,
                tags=[str(t) for t in tags][:12],
                posted_at=str(item.get("pubDate") or item.get("published_at") or "") or None,
            )
        )

    if keywords:
        scored = []
        for j in out:
            blob = f"{j.title} {j.company} {' '.join(j.tags)} {j.description or ''}".lower()
            hits = sum(1 for k in keywords if k in blob)
            scored.append((hits, j))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = [j for _, j in scored]
    return out[:limit]


async def _fetch_jsearch_stub(
    settings: Settings,
    *,
    query: str | None,
    limit: int,
) -> list[JobPosting]:
    """Optional RapidAPI JSearch stub — disabled when JSEARCH_API_KEY is unset."""
    if not settings.jsearch_enabled:
        return []
    # Stub: real RapidAPI call omitted on free-tier default; returns empty when key present
    # but network blocked. Kept as attribution-ready source for future enablement.
    logger.info("JSearch stub invoked (key set); returning empty list in free-tier mode")
    _ = (query, limit)
    return []


def merge_and_dedupe(jobs: list[JobPosting]) -> list[JobPosting]:
    seen: set[str] = set()
    merged: list[JobPosting] = []
    for job in jobs:
        key = _dedupe_key(job.apply_url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(job)
    return merged


async def search_jobs(
    *,
    query: str = "AI engineer",
    geo: str | None = "philippines",
    tag: str | None = None,
    limit: int = 15,
    settings: Settings | None = None,
    db: SupabaseService | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[JobPosting]:
    """Query Himalayas + Jobicy concurrently, merge, dedupe by URL, cache in Supabase."""
    settings = settings or get_settings()
    db = db or get_db()
    cache_key = f"search:{query}:{geo}:{tag}:{limit}"
    cached = db.get_jobs_cache(cache_key, settings.jobs_cache_ttl_s)
    if cached is not None:
        return [JobPosting.model_validate(j) for j in cached]

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=settings.tool_timeout_s)
    try:
        him_task = _fetch_himalayas(client, query=query, limit=limit)
        job_task = _fetch_jobicy(client, query=query, geo=geo, tag=tag, limit=limit)
        him_jobs, job_jobs = await asyncio.gather(him_task, job_task)
        jsearch_jobs = await _fetch_jsearch_stub(settings, query=query, limit=limit)
        merged = merge_and_dedupe([*him_jobs, *job_jobs, *jsearch_jobs])[:limit]
    finally:
        if owns_client:
            await client.aclose()

    db.set_jobs_cache(cache_key, [j.model_dump() for j in merged])
    return merged


async def fetch_posting(
    *,
    url: str | None = None,
    job_id: str | None = None,
    settings: Settings | None = None,
    db: SupabaseService | None = None,
    client: httpx.AsyncClient | None = None,
) -> JobPosting | dict[str, Any]:
    """Fetch a single posting by URL or look up from recent cache by id."""
    settings = settings or get_settings()
    db = db or get_db()

    if job_id:
        from app.services.supabase_client import _memory

        for bucket in _memory.get("jobs_cache", {}).values():
            for raw in bucket.get("jobs") or []:
                if raw.get("id") == job_id:
                    return JobPosting.model_validate(raw)

    if not url:
        return {"error": "Provide url or a cached job_id"}

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=settings.tool_timeout_s, follow_redirects=True)
    try:
        resp = await client.get(url)
        text = resp.text[:8000] if resp.is_success else ""
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I)
        title = title_match.group(1).strip() if title_match else "Job posting"
        # Strip common suffixes
        title = re.sub(r"\s*[|\-–].*$", "", title).strip() or title
        host = urlparse(url).netloc.lower()
        if "himalayas" in host:
            source: Any = "Himalayas"
        elif "jobicy" in host:
            source = "Jobicy"
        else:
            # Unknown host: JSearch only when enabled, else Jobicy as remote default
            source = "JSearch" if settings.jsearch_enabled else "Jobicy"
        return JobPosting(
            id=_job_id(str(source), url, title, host),
            title=title,
            company=host,
            location=None,
            description=re.sub(r"<[^>]+>", " ", text)[:3000].strip() or None,
            apply_url=url,
            source=source,
            tags=[],
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"fetch_posting failed: {exc}"}
    finally:
        if owns_client:
            await client.aclose()
