from sqlalchemy import create_engine
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
