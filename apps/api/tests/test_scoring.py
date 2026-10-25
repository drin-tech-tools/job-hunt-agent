from app.models.schemas import JobPosting
from app.tools.scoring import draft_cover_letter, score_fit
from tests.conftest import RESUME_TEXT


def test_score_fit_structured() -> None:
    job = JobPosting(
        id="abc",
        title="ML Engineer",
        company="Acme",
        apply_url="https://himalayas.app/jobs/1",
        source="Himalayas",
        description="Python PyTorch LLM RAG FastAPI Kubernetes",
        tags=["Python", "AI"],
    )
    fit = score_fit(RESUME_TEXT, job)
    assert 0 <= fit.score <= 100
    assert isinstance(fit.matched_skills, list)
    assert isinstance(fit.gaps, list)
    assert fit.score >= 50


def test_draft_cover_letter() -> None:
    job = JobPosting(
        id="abc",
        title="ML Engineer",
        company="Acme",
        apply_url="https://jobicy.com/jobs/1",
        source="Jobicy",
        description="Python LLM",
        tags=["Python"],
    )
    draft = draft_cover_letter(RESUME_TEXT, job)
    assert "Acme" in draft.body
    assert draft.subject
