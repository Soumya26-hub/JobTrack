from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "sqlite:///./jobtrack.db"

engine = create_engine(
    DATABASE_URL,
    # SQLite connections may be used by different request-handling threads.
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Give each request its own database session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns():
    """
    create_all() makes new tables but never changes existing ones. If the database
    was created by an older version of the app, add any new columns so it keeps working
    without deleting saved applications.
    """
    existing = {column["name"] for column in inspect(engine).get_columns("applications")}
    new_columns = {
        "job_description": "TEXT",
        "match_score": "INTEGER",
        "tailored_summary": "TEXT",
        "source": "VARCHAR",
        "external_id": "VARCHAR",
    }
    with engine.begin() as connection:
        for name, sql_type in new_columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE applications ADD COLUMN {name} {sql_type}"))
