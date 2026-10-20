from datetime import date, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .models import STATUSES, Application
from .schemas import ApplicationCreate, ApplicationUpdate


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

    # Only change the fields the client actually sent. Required columns are
    # never cleared, even if the client sends them as null.
    for field, value in data.model_dump(exclude_unset=True).items():
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
