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
