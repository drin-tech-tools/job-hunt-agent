"""Job search merge/dedupe/attribution tests with mocked HTTP."""

from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.models.schemas import JobPosting
from app.tools.jobs import merge_and_dedupe, search_jobs
from tests.conftest import HIMALAYAS_SAMPLE, JOBICY_SAMPLE


@pytest.mark.asyncio
async def test_search_jobs_merges_and_dedupes(httpx_mock: HTTPXMock) -> None:
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

    jobs = await search_jobs(query="AI Python", geo="philippines", limit=15)
    assert len(jobs) >= 2
    sources = {j.source for j in jobs}
    assert sources & {"Himalayas", "Jobicy"}
    for j in jobs:
        assert j.apply_url
        assert j.source in ("Himalayas", "Jobicy", "JSearch")

    urls = [_norm(j.apply_url) for j in jobs]
    assert len(urls) == len(set(urls))


def _norm(url: str) -> str:
    from urllib.parse import urlparse

    p = urlparse(url)
    return f"{p.netloc.removeprefix('www.')}{p.path.rstrip('/')}"


def test_merge_dedupe_by_url() -> None:
    a = JobPosting(
        id="1",
        title="A",
        company="C",
        apply_url="https://example.com/job/1",
        source="Himalayas",
    )
    b = JobPosting(
        id="2",
        title="A dup",
        company="C",
        apply_url="https://www.example.com/job/1/",
        source="Jobicy",
    )
    merged = merge_and_dedupe([a, b])
    assert len(merged) == 1
