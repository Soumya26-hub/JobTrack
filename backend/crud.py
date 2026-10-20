from datetime import date, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import job_sources, resume_agent
from .config import load_settings
from .default_profile import DEFAULT_PROFILE
from .models import STATUSES, Application, ResumeProfile
from .schemas import ApplicationCreate, ApplicationUpdate, JobPaste, JobSave, MatchRequest, ProfileUpdate


FOLLOW_UP_AFTER_DAYS = 7
# Statuses that mean the company replied (anything beyond "Applied").
RESPONDED_STATUSES = ("Interview", "Offer", "Rejected")
REQUIRED_FIELDS = ("company", "role", "status", "applied_date")


def create_application(db: Session, data: ApplicationCreate) -> Application:
    values = data.model_dump()
    values["applied_date"] = values["applied_date"] or date.today()

    # Remind me to follow up a week after applying, unless I chose a date myself.
    if values["follow_up_date"] is None and values["status"] == "Applied":
        values["follow_up_date"] = values["applied_date"] + timedelta(days=FOLLOW_UP_AFTER_DAYS)

    application = Application(**values)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def get_applications(
    db: Session,
    status: str | None = None,
    search: str | None = None,
) -> list[Application]:
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(Application.company.ilike(pattern), Application.role.ilike(pattern))
        )
    # Newest applications first; id breaks ties for the same day.
    return query.order_by(Application.applied_date.desc(), Application.id.desc()).all()


def get_application(db: Session, application_id: int) -> Application | None:
    return db.query(Application).filter(Application.id == application_id).first()


def update_application(
    db: Session,
    application_id: int,
    data: ApplicationUpdate,
) -> Application | None:
    application = get_application(db, application_id)
    if application is None:
        return None

    changes = data.model_dump(exclude_unset=True)

    # A job saved to the Wishlist weeks ago and applied to today gets today's date and
    # a fresh reminder, unless the request sets those dates itself.
    if application.status == "Wishlist" and changes.get("status") == "Applied":
        changes.setdefault("applied_date", date.today())
        changes.setdefault("follow_up_date", date.today() + timedelta(days=FOLLOW_UP_AFTER_DAYS))

    # Only change the fields the client actually sent. Required columns are
    # never cleared, even if the client sends them as null.
    for field, value in changes.items():
        if value is None and field in REQUIRED_FIELDS:
            continue
        setattr(application, field, value)

    db.commit()
    db.refresh(application)
    return application


def delete_application(db: Session, application_id: int) -> Application | None:
    application = get_application(db, application_id)
    if application is None:
        return None

    db.delete(application)
    db.commit()
    return application


def get_follow_ups_due(db: Session) -> list[Application]:
    """Applications still waiting for a reply whose follow-up date has arrived."""
    return (
        db.query(Application)
        .filter(Application.status == "Applied")
        .filter(Application.follow_up_date <= date.today())
        .order_by(Application.follow_up_date)
        .all()
    )


def get_stats(db: Session) -> dict:
    # One GROUP BY query counts applications in every status at once.
    rows = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    by_status = {status: 0 for status in STATUSES}
    by_status.update(dict(rows))

    sent = sum(count for status, count in by_status.items() if status != "Wishlist")
    responded = sum(by_status[status] for status in RESPONDED_STATUSES)
    response_rate = round(responded / sent * 100, 1) if sent else 0.0

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "response_rate": response_rate,
        "follow_ups_due": len(get_follow_ups_due(db)),
    }


# ---------- Resume profile and Resume Match agent ----------

def get_profile(db: Session) -> ResumeProfile:
    """Return my resume profile, creating it from the default the first time."""
    profile = db.query(ResumeProfile).first()
    if profile is None:
        profile = ResumeProfile(**DEFAULT_PROFILE)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def profile_dict(db: Session) -> dict:
    """The profile as the plain dict the Resume Match agent expects."""
    profile = get_profile(db)
    return {"intro": profile.intro, "skills": profile.skills, "highlights": profile.highlights}


def update_profile(db: Session, data: ProfileUpdate) -> ResumeProfile:
    profile = get_profile(db)
    for field, value in data.model_dump().items():
        setattr(profile, field, value.strip())
    db.commit()
    db.refresh(profile)
    return profile


def run_resume_match(db: Session, request: MatchRequest) -> dict | None:
    """
    Compare a job description with my profile. If an application id is given,
    save the description, score and summary on it. Returns None if that id doesn't exist.
    """
    application = None
    if request.application_id is not None:
        application = get_application(db, request.application_id)
        if application is None:
            return None

    result = resume_agent.analyze(request.job_description, profile_dict(db))

    if application is not None:
        application.job_description = request.job_description
        application.match_score = result["match_score"]
        application.tailored_summary = result["tailored_summary"]
        db.commit()
        result["saved_to_application"] = application.id

    return result


# ---------- Find Jobs ----------

MAX_SEARCH_RESULTS = 50
UNKNOWN_ROLE = "Unknown role"


def job_source_status() -> list[dict]:
    return job_sources.source_status(load_settings())


def search_jobs(db: Session, role: str, location: str) -> dict:
    """Search every configured source, score each job against my resume, best match first."""
    result = job_sources.search_all(role.strip(), location.strip(), load_settings())
    profile = profile_dict(db)
    # One query for all saved links, instead of one query per job.
    saved_links = {link for (link,) in db.query(Application.job_link).filter(Application.job_link.isnot(None))}

    for job in result["jobs"]:
        match = resume_agent.analyze(job["description"], profile)
        job["match_score"] = match["match_score"]
        job["matched_skills"] = match["matched_skills"]
        job["missing_skills"] = match["missing_skills"]
        job["already_saved"] = job["url"] in saved_links

    result["jobs"].sort(key=lambda job: job["match_score"], reverse=True)
    result["jobs"] = result["jobs"][:MAX_SEARCH_RESULTS]
    return result


def link_already_saved(db: Session, job_link: str | None) -> bool:
    if not job_link:
        return False
    return db.query(Application.id).filter(Application.job_link == job_link).first() is not None


def save_scored_job(db: Session, *, company, role, location, job_link, description, source, external_id):
    """
    Save a found or pasted job to the Wishlist, with a fresh Resume Match score.
    Returns None if the same link is already in the tracker.
    """
    if link_already_saved(db, job_link):
        return None

    match = resume_agent.analyze(description, profile_dict(db))
    application = Application(
        company=company,
        role=role,
        location=location or None,
        job_link=job_link,
        # Wishlist: saved to apply later, so no follow-up reminder yet.
        status="Wishlist",
        applied_date=date.today(),
        job_description=description,
        match_score=match["match_score"],
        tailored_summary=match["tailored_summary"],
        source=source,
        external_id=external_id or None,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def save_job(db: Session, job: JobSave) -> Application | None:
    return save_scored_job(
        db,
        company=job.company,
        role=job.title,
        location=job.location,
        job_link=job.url,
        description=job.description,
        source=job.source,
        external_id=job.external_id,
    )


def paste_job(db: Session, data: JobPaste) -> Application | None:
    """A job copied by hand. If no role is typed, read it from a 'Job Title:' line."""
    role = (data.role or "").strip() or resume_agent.find_job_title(data.job_description) or UNKNOWN_ROLE
    return save_scored_job(
        db,
        company=data.company,
        role=role[:100],
        location=(data.location or "").strip(),
        job_link=data.job_link,
        description=data.job_description,
        source="Pasted",
        external_id=None,
    )
