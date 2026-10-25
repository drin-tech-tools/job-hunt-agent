"""Pydantic models for API payloads and tool I/O."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TrackerStatus(StrEnum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


JobSource = Literal["Himalayas", "Jobicy", "JSearch"]


class JobPosting(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    description: str | None = None
    apply_url: str = Field(..., description="Original apply URL (required by job board terms)")
    source: JobSource
    salary: str | None = None
    tags: list[str] = Field(default_factory=list)
    posted_at: str | None = None

    @field_validator("apply_url")
    @classmethod
    def require_apply_url(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("apply_url is required for attribution")
        return str(v).strip()


class FitScore(BaseModel):
    score: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rationale: str = ""


class CoverLetterDraft(BaseModel):
    subject: str
    body: str
    job_id: str | None = None
    job_title: str | None = None
    company: str | None = None


class StepTrace(BaseModel):
    step: int
    thought_summary: str = ""
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    ms: int = 0
    error: str | None = None


class AgentRunRequest(BaseModel):
    resume_id: str | None = None
    resume_text: str | None = None
    query: str = Field(
        default="Find remote AI/ML engineering roles that match my resume and score the top fits.",
        min_length=1,
    )
    max_jobs: int = Field(default=8, ge=1, le=20)
    location: str | None = "philippines"
    tags: list[str] = Field(default_factory=lambda: ["ai", "machine-learning", "python"])


class ScoredJob(BaseModel):
    job: JobPosting
    fit: FitScore | None = None
    cover_letter: CoverLetterDraft | None = None


class AgentRunSummary(BaseModel):
    run_id: str | None = None
    status: Literal["ok", "error", "timeout"] = "ok"
    message: str = ""
    steps: list[StepTrace] = Field(default_factory=list)
    jobs: list[ScoredJob] = Field(default_factory=list)
    model_used: str | None = None


class ResumeCreate(BaseModel):
    title: str = "My Resume"
    content: str = Field(..., min_length=20)
    skills: list[str] = Field(default_factory=list)


class ResumeOut(BaseModel):
    id: str
    title: str
    content: str
    skills: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrackerCreate(BaseModel):
    job_id: str
    title: str
    company: str
    apply_url: str
    source: JobSource
    status: TrackerStatus = TrackerStatus.saved
    score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    cover_letter: str | None = None


class TrackerUpdate(BaseModel):
    status: TrackerStatus | None = None
    notes: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    cover_letter: str | None = None


class TrackerOut(BaseModel):
    id: str
    job_id: str
    title: str
    company: str
    apply_url: str
    source: JobSource
    status: TrackerStatus
    score: int | None = None
    notes: str | None = None
    cover_letter: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

