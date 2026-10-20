# JobTrack: notes for Claude Code

## What this is
A small, mobile-friendly job application tracker. It is a portfolio project for a
software development job search, and its owner must be able to explain every line
in an interview. Keep it simple and readable.

## Stack (do not add to it)
- Backend: Python, FastAPI, SQLAlchemy ORM, SQLite, Pydantic
- Frontend: plain HTML, CSS, JavaScript (no frameworks, no build step)
- Do NOT add new libraries, frameworks, Docker, auth, or AI features unless asked.
  Testing during development may use FastAPI's TestClient (needs `httpx`), but
  do not add test files to the project unless asked.

## Layout
- `backend/main.py`: routes and app startup (lifespan creates tables)
- `backend/crud.py`: all database reads and writes, stats, follow-ups
- `backend/models.py`: `Application` table, with a status CHECK constraint
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
- Platform is Windows. Use `venv\Scripts\activate` and `python`, not `python3`.

## Run
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```
Open http://localhost:8000 (API docs at /docs).
