from datetime import date

from sqlalchemy import CheckConstraint, Column, Date, Integer, String, Text

from .database import Base


# The stages an application can be in, in the order they usually happen.
STATUSES = ("Wishlist", "Applied", "Interview", "Offer", "Rejected")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        # Reject any status outside the allowed list at the database level too.
        CheckConstraint(
            "status IN ('Wishlist', 'Applied', 'Interview', 'Offer', 'Rejected')",
            name="ck_application_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    location = Column(String)
    job_link = Column(String)
    status = Column(String, nullable=False, default="Applied", index=True)
    applied_date = Column(Date, nullable=False, default=date.today)
    follow_up_date = Column(Date)
    notes = Column(Text)

    # Filled in by the Resume Match agent when it is run for this application.
    job_description = Column(Text)
    match_score = Column(Integer)
    tailored_summary = Column(Text)


class ResumeProfile(Base):
    """My resume content that the Resume Match agent compares against. One row only."""

    __tablename__ = "resume_profile"

    id = Column(Integer, primary_key=True)
    intro = Column(String, nullable=False)
    skills = Column(Text, nullable=False)
    highlights = Column(Text, nullable=False)
