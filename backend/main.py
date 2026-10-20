from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import crud
from .database import Base, add_missing_columns, engine, get_db
from .schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    JobPaste,
    JobSave,
    JobSearchResponse,
    JobSourceStatus,
    MatchRequest,
    MatchResult,
    ProfileRead,
    ProfileUpdate,
    Stats,
    Status,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the tables once when the server starts, and upgrade an older database.
    Base.metadata.create_all(bind=engine)
    add_missing_columns()
    yield


app = FastAPI(title="JobTrack", description="Track my job applications.", lifespan=lifespan)


def get_or_404(db: Session, application_id: int):
    application = crud.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@app.post("/api/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    return crud.create_application(db, data)


@app.get("/api/applications", response_model=list[ApplicationRead])
def list_applications(
    status: Status | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.get_applications(db, status, search)


# Fixed paths are declared before /{application_id} so they are not read as an id.
@app.get("/api/applications/stats", response_model=Stats)
def application_stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)


@app.get("/api/applications/follow-ups", response_model=list[ApplicationRead])
def follow_ups_due(db: Session = Depends(get_db)):
    return crud.get_follow_ups_due(db)


@app.get("/api/applications/{application_id}", response_model=ApplicationRead)
def read_application(application_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, application_id)


@app.patch("/api/applications/{application_id}", response_model=ApplicationRead)
def update_application(application_id: int, data: ApplicationUpdate, db: Session = Depends(get_db)):
    application = crud.update_application(db, application_id, data)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@app.delete("/api/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    if crud.delete_application(db, application_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")


# ---------- Resume Match agent ----------

@app.get("/api/profile", response_model=ProfileRead)
def read_profile(db: Session = Depends(get_db)):
    return crud.get_profile(db)


@app.put("/api/profile", response_model=ProfileRead)
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db)):
    return crud.update_profile(db, data)


@app.post("/api/agent/resume-match", response_model=MatchResult)
def resume_match(request: MatchRequest, db: Session = Depends(get_db)):
    result = crud.run_resume_match(db, request)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return result


# ---------- Find Jobs ----------

ALREADY_SAVED = "Already in your tracker"


@app.get("/api/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    role: str = Query(min_length=2, max_length=100),
    location: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
):
    return crud.search_jobs(db, role, location)


@app.get("/api/jobs/sources", response_model=list[JobSourceStatus])
def job_sources_status():
    return crud.job_source_status()


@app.post("/api/jobs/save", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def save_job(job: JobSave, db: Session = Depends(get_db)):
    application = crud.save_job(db, job)
    if application is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_SAVED)
    return application


@app.post("/api/jobs/paste", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def paste_job(data: JobPaste, db: Session = Depends(get_db)):
    application = crud.paste_job(db, data)
    if application is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_SAVED)
    return application


# Serve the web page from the same server, so the phone only needs one address.
frontend_directory = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
