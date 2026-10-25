"""Heuristic + optional Gemini-backed fit scoring and cover letter drafting."""

from __future__ import annotations

import re
from typing import Any

from app.models.schemas import CoverLetterDraft, FitScore, JobPosting


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}", text.lower()) if len(t) > 1}


# Common skill-ish tokens to prioritize in matching
SKILL_HINTS = {
    "python",
    "typescript",
    "javascript",
    "react",
    "nextjs",
    "next.js",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgres",
    "postgresql",
    "mongodb",
    "redis",
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "k8s",
    "ml",
    "ai",
    "llm",
    "nlp",
    "pytorch",
    "tensorflow",
    "sklearn",
    "scikit-learn",
    "langchain",
    "langgraph",
    "rag",
    "vector",
    "embeddings",
    "spark",
    "airflow",
    "dbt",
    "snowflake",
    "kafka",
    "graphql",
    "rest",
    "cicd",
    "git",
    "linux",
    "golang",
    "go",
    "rust",
    "java",
    "kotlin",
    "swift",
    "terraform",
    "ansible",
    "pandas",
    "numpy",
    "huggingface",
    "openai",
    "gemini",
    "agents",
    "mlops",
    "data",
    "etl",
}


def score_fit(resume_text: str, job: JobPosting | dict[str, Any]) -> FitScore:
    """Return structured fit score 0–100 with matched skills and gaps (Pydantic-validated)."""
    if isinstance(job, dict):
        job = JobPosting.model_validate(job)

    resume_tokens = _tokenize(resume_text)
    job_blob = " ".join(
        [
            job.title,
            job.company,
            job.description or "",
            " ".join(job.tags),
            job.location or "",
        ]
    )
    job_tokens = _tokenize(job_blob)

    resume_skills = resume_tokens & SKILL_HINTS
    job_skills = job_tokens & SKILL_HINTS
    # Also treat multi-word-ish tags as skills
    for tag in job.tags:
        t = tag.lower().strip()
        if t:
            job_skills.add(t.split()[0] if " " in t else t)

    matched = sorted(resume_skills & job_skills)
    gaps = sorted(job_skills - resume_skills)

    if not job_skills:
        # Fallback overlap on general tokens
        overlap = resume_tokens & job_tokens
        matched = sorted(list(overlap)[:12])
        base = min(85, 40 + len(overlap) * 2)
        return FitScore(
            score=base,
            matched_skills=matched,
            gaps=[],
            rationale="General keyword overlap (few explicit skills in posting).",
        )

    coverage = len(matched) / max(len(job_skills), 1)
    title_l = job.title.lower()
    title_boost = 8 if any(k in title_l for k in ("ai", "ml", "machine", "llm", "data")) else 0
    score = int(round(min(100, max(0, coverage * 85 + title_boost + min(10, len(matched))))))
    rationale = (
        f"Matched {len(matched)}/{len(job_skills)} posting skills"
        + (f"; gaps: {', '.join(gaps[:5])}" if gaps else ".")
    )
    return FitScore(score=score, matched_skills=matched, gaps=gaps, rationale=rationale)


def draft_cover_letter(
    resume_text: str,
    job: JobPosting | dict[str, Any],
    fit: FitScore | None = None,
) -> CoverLetterDraft:
    """Draft a concise, tailored cover letter from resume + posting."""
    if isinstance(job, dict):
        job = JobPosting.model_validate(job)
    fit = fit or score_fit(resume_text, job)

    # Pull a name-ish first line from resume if present
    first_line = (resume_text.strip().splitlines() or ["Candidate"])[0].strip()
    candidate = first_line[:80] if len(first_line) < 80 else "Candidate"

    skills = ", ".join(fit.matched_skills[:6]) or "relevant experience"
    gap_note = ""
    if fit.gaps:
        gap_note = (
            f" I am actively deepening my work in {', '.join(fit.gaps[:3])}"
            " and would welcome the chance to grow those areas on your team."
        )

    body = (
        f"Dear {job.company} Hiring Team,\n\n"
        f"I am writing to apply for the {job.title} role. "
        f"My background aligns well with this posting — particularly around {skills} "
        f"(estimated fit score {fit.score}/100).{gap_note}\n\n"
        f"A few highlights from my experience:\n"
        f"- Built and shipped production systems involving modern AI/ML tooling\n"
        f"- Comfortable across the stack from data pipelines to API design\n"
        f"- Motivated by clear product impact and careful engineering\n\n"
        f"I would welcome a conversation about how I can contribute at {job.company}. "
        f"Thank you for your time and consideration.\n\n"
        f"Sincerely,\n{candidate}"
    )
    return CoverLetterDraft(
        subject=f"Application: {job.title} at {job.company}",
        body=body,
        job_id=job.id,
        job_title=job.title,
        company=job.company,
    )
