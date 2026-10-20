from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Status = Literal["Wishlist", "Applied", "Interview", "Offer", "Rejected"]


# Shared by create and update, so editing follows the same rules as adding.
def require_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def check_link(value: str | None) -> str | None:
    # Only web links, so a "javascript:" link can never be saved and clicked.
    if value and not value.startswith(("http://", "https://")):
        raise ValueError("job link must start with http:// or https://")
    return value or None


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    location: str | None = None
    job_link: str | None = None
    status: Status = "Applied"
    applied_date: date | None = None
    follow_up_date: date | None = None
    notes: str | None = None

    _require_text = field_validator("company", "role")(require_text)
    _check_link = field_validator("job_link")(check_link)


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = None
    job_link: str | None = None
    status: Status | None = None
    applied_date: date | None = None
    follow_up_date: date | None = None
    notes: str | None = None

    _require_text = field_validator("company", "role")(require_text)
    _check_link = field_validator("job_link")(check_link)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: str | None
    job_link: str | None
    status: str
    applied_date: date
    follow_up_date: date | None
    notes: str | None
    job_description: str | None = None
    match_score: int | None = None
    tailored_summary: str | None = None
    source: str | None = None
    external_id: str | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intro: str
    skills: str
    highlights: str


class ProfileUpdate(BaseModel):
    intro: str = Field(min_length=1)
    skills: str = Field(min_length=1)
    highlights: str = Field(min_length=1)


class MatchRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=20000)
    # Optional: save the result on this application.
    application_id: int | None = None

    @field_validator("job_description")
    @classmethod
    def require_full_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 20:
            raise ValueError("paste the full job description (at least 20 characters)")
        return value


class MatchResult(BaseModel):
    job_title: str | None
    years_required: int | None
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    tailored_summary: str
    saved_to_application: int | None = None


# ---------- Find Jobs ----------

class JobSave(BaseModel):
    """One job from the search results, sent back when the user taps Save."""

    source: str = Field(min_length=1, max_length=50)
    external_id: str = Field(default="", max_length=200)
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=200)
    location: str = Field(default="", max_length=500)
    url: str = Field(min_length=1, max_length=2000)
    description: str = Field(default="", max_length=20000)
    posted: str | None = None

    _check_link = field_validator("url")(check_link)


class JobResult(JobSave):
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    already_saved: bool = False


class JobSearchResponse(BaseModel):
    jobs: list[JobResult]
    warnings: list[str]
    sources_used: list[str]


class JobSourceStatus(BaseModel):
    name: str
    ready: bool


class JobPaste(BaseModel):
    """A job copied by hand from LinkedIn, Naukri or anywhere else."""

    job_description: str = Field(min_length=20, max_length=50000)
    company: str = Field(min_length=1, max_length=100)
    role: str | None = Field(default=None, max_length=100)
    location: str | None = None
    job_link: str | None = None

    _require_text = field_validator("company")(require_text)
    _check_link = field_validator("job_link")(check_link)

    @field_validator("job_description")
    @classmethod
    def require_full_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 20:
            raise ValueError("paste the full job description (at least 20 characters)")
        return value


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]
    response_rate: float
    follow_ups_due: int
