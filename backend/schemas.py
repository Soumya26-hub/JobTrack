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


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]
    response_rate: float
    follow_ups_due: int
