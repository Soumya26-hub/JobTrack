# JobTrack: notes for Claude Code

## What this is
A small, mobile-friendly job application tracker. It is a portfolio project for a
software development job search, and its owner must be able to explain every line
in an interview. Keep it simple and readable.

## Stack (do not add to it)
- Backend: Python, FastAPI, SQLAlchemy ORM, SQLite, Pydantic
- Frontend: plain HTML, CSS, JavaScript (no frameworks, no build step)
- Do NOT add new libraries, frameworks, Docker, auth, or AI provider/LLM packages
  unless asked. The Resume Match agent is deliberately rule-based (pure Python).
  Testing during development may use FastAPI's TestClient (needs `httpx`), but
  do not add test files to the project unless asked.

## Feature specs
- `docs/FIND_JOBS_SPEC.md`: the Find Jobs feature (job-search APIs + Paste job). Built; follow it when changing that feature.

## Layout
- `backend/main.py`: routes and app startup (lifespan creates tables)
- `backend/crud.py`: all database reads and writes, stats, follow-ups, agent runs
- `backend/resume_agent.py`: Resume Match agent. Pure Python, no database or FastAPI
  imports, so it can be tested on its own. Skill dictionary is `SKILLS`.
- `backend/default_profile.py`: starting resume profile (seeded on first use)
- `backend/job_sources.py`: Adzuna, Jooble, Greenhouse and Lever calls; every source
  returns the same job dict. `fetch_json` is the only network call (patch it in tests).
- `backend/config.py`: reads job-search keys from `.env` with a small parser of its own
- `backend/models.py`: `Application` (status CHECK constraint) and `ResumeProfile`
- `backend/schemas.py`: Pydantic request and response models
- `backend/database.py`: engine, session, `get_db`
- `frontend/`: `index.html`, `app.js`, `style.css`, `manifest.json`, icons
- `start-for-phone.bat`: runs the server on 0.0.0.0:8000 for phone access

## Rules
- Fixed routes (`/stats`, `/follow-ups`) must stay above `/{application_id}` in main.py.
- Statuses are exactly: Wishlist, Applied, Interview, Offer, Rejected.
  If they change, update models.py, schemas.py, crud.py and app.js together.
- In the frontend, insert user text with `textContent`, never `innerHTML`.
- Keep the short comments that explain *why*; they help in interviews.
- The agent must never invent experience: summaries only reuse the profile's
  intro and highlights. Missing skills are shown, never added automatically.
- New columns on `applications` must also be added to `add_missing_columns()` in
  database.py, because `create_all()` does not alter existing tables.
- HTTP calls use urllib only (no `requests`, `httpx` or other packages in the app).
- Keys come from `.env`, never from code. Only `.env.example`, with empty values, is committed.
- Never scrape sites that forbid it (LinkedIn, Naukri, Indeed). Their jobs come in
  only through Paste job.
- Platform is Windows. Use `venv\Scripts\activate` and `python`, not `python3`.

## Run
```
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```
Open http://localhost:8000 (API docs at /docs).
