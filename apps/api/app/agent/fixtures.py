"""Deterministic fixture jobs and LLM-ish outputs for AGENT_MOCK mode."""

from __future__ import annotations

from app.models.schemas import CoverLetterDraft, FitScore, JobPosting, ScoredJob

# Stable IDs so Apply URLs and tracker assertions stay deterministic across runs.
FIXTURE_JOBS: list[JobPosting] = [
    JobPosting(
        id="mock-him-ml-001",
        title="Senior ML Engineer",
        company="Acme AI",
        location="Worldwide / Remote",
        description=(
            "Build LLM agents with Python, FastAPI, PyTorch, and RAG. "
            "Own scoring pipelines and evaluation harnesses."
        ),
        apply_url="https://himalayas.app/companies/acme/jobs/senior-ml-engineer",
        source="Himalayas",
        tags=["AI", "Python", "Machine Learning", "RAG"],
        posted_at="2026-01-01",
    ),
    JobPosting(
        id="mock-jobicy-ai-002",
        title="AI Platform Engineer",
        company="Orbital Labs",
        location="Philippines / Anywhere",
        description=(
            "Python, Kubernetes, LLMOps, FastAPI microservices. "
            "Ship production agent tooling for remote teams."
        ),
        apply_url="https://jobicy.com/jobs/ai-platform-engineer",
        source="Jobicy",
        tags=["AI", "Python", "Kubernetes", "FastAPI"],
        posted_at="2026-01-03",
    ),
    JobPosting(
        id="mock-him-data-003",
        title="Data Engineer (LLM Pipelines)",
        company="Cascade Analytics",
        location="APAC Remote",
        description="Spark, dbt, vector stores, and eval datasets for RAG products.",
        apply_url="https://himalayas.app/companies/cascade/jobs/data-engineer-llm",
        source="Himalayas",
        tags=["Data", "Python", "Spark", "RAG"],
        posted_at="2026-01-05",
    ),
]

FIXTURE_FITS: dict[str, FitScore] = {
    "mock-him-ml-001": FitScore(
        score=92,
        matched_skills=["Python", "FastAPI", "PyTorch", "LLM", "RAG"],
        gaps=["Spark"],
        rationale="Strong agent/RAG overlap; missing Spark depth.",
    ),
    "mock-jobicy-ai-002": FitScore(
        score=88,
        matched_skills=["Python", "FastAPI", "Kubernetes", "LLM"],
        gaps=["GCP"],
        rationale="Platform + LLMOps fit; cloud cert gap.",
    ),
    "mock-him-data-003": FitScore(
        score=74,
        matched_skills=["Python", "RAG", "SQL"],
        gaps=["Spark", "dbt"],
        rationale="Partial data-platform overlap.",
    ),
}


def fixture_cover_letter(job: JobPosting, fit: FitScore) -> CoverLetterDraft:
    return CoverLetterDraft(
        subject=f"Application — {job.title} at {job.company}",
        body=(
            f"Dear {job.company} hiring team,\n\n"
            f"I am excited to apply for the {job.title} role. "
            f"My background in {', '.join(fit.matched_skills[:4])} aligns with your needs. "
            f"I am eager to close gaps around {', '.join(fit.gaps[:2]) or 'continued learning'} "
            f"while contributing from day one.\n\n"
            "Thank you for your consideration.\n\nBest regards,\nCandidate"
        ),
        job_id=job.id,
        job_title=job.title,
        company=job.company,
    )


def scored_fixture_jobs(max_jobs: int = 8) -> list[ScoredJob]:
    out: list[ScoredJob] = []
    for job in FIXTURE_JOBS[:max_jobs]:
        fit = FIXTURE_FITS[job.id]
        out.append(
            ScoredJob(
                job=job,
                fit=fit,
                cover_letter=fixture_cover_letter(job, fit),
            )
        )
    return out


# Special query markers used by BDD scenarios (deterministic mock branches).
MOCK_MARKER_MAX_STEPS = "[max_steps]"
MOCK_MARKER_SOURCE_FAILURE = "[source_failure]"
MOCK_MARKER_TIMEOUT = "[timeout]"
