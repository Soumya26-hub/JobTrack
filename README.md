# JobTrack

A mobile-friendly web app for tracking job applications: log every application,
move it through each stage, get reminded to follow up, and see how the search is going.

## Features

- Add, view, edit and delete job applications
- Track each application through five stages: Wishlist, Applied, Interview, Offer, Rejected
- Automatic follow-up reminder 7 days after applying (or a date you choose)
- Dashboard with totals, interviews, offers and response rate
- Search by company or role, and filter by status
- **Resume Match agent:** paste a job description to get a match score, the skills you
  have and the ones to review, and a resume summary tailored to that job
- Works on a phone and can be added to the home screen like an app

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy ORM, SQLite, Pydantic
- **Frontend:** HTML, CSS, JavaScript (no framework)

## Run It

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Open http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.

### Open it on a phone

Start the server so other devices on the same Wi-Fi can reach it:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Find the computer's local IP address (`ipconfig` on Windows, look for "IPv4 Address"),
then open `http://<that-ip>:8000` in the phone's browser. Use the browser menu's
**Add to Home screen** option to install it like an app.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/applications` | Add an application |
| GET | `/api/applications?status=&search=` | List applications, with optional filters |
| GET | `/api/applications/{id}` | Get one application |
| PATCH | `/api/applications/{id}` | Update some fields of an application |
| DELETE | `/api/applications/{id}` | Delete an application |
| GET | `/api/applications/stats` | Totals per status and response rate |
| GET | `/api/applications/follow-ups` | Applications due for a follow-up |
| GET | `/api/profile` | My resume profile used by the agent |
| PUT | `/api/profile` | Update the resume profile |
| POST | `/api/agent/resume-match` | Compare a job description with my resume |

## How It Works

- **Validation** happens twice: Pydantic checks every request (required fields,
  allowed statuses, link format), and the database has a check constraint so an
  invalid status can never be saved.
- **Response rate** = applications that got a reply (Interview, Offer or Rejected)
  ÷ applications sent (everything except Wishlist).
- **Stats** use one SQL `GROUP BY` query instead of loading every row into Python.
- **Follow-ups** are applications still in "Applied" whose follow-up date is today or earlier.

## Resume Match Agent

The agent is rule-based, so it needs no AI provider, API key or internet connection,
and it gives the same answer every time for the same input.

1. **Find the job's skills:** a dictionary of about 55 skills, each with regular
   expressions (for example `postgres` or `postgresql` both mean PostgreSQL), is
   matched against the job description.
2. **Find my skills:** the same dictionary is matched against my resume profile.
3. **Compare:** matched skills, missing skills and a score
   (matched ÷ skills the job asks for).
4. **Write the summary:** an opening line with my top matched skills, then the three
   resume highlights that mention the most of the job's skills (technical skills
   count double), kept in their original order. It is *extractive*: it only reuses
   sentences from my profile, so it never claims experience I don't have.

If an application is chosen, the job description, score and summary are saved on it.
The profile is stored in the database and can be edited on the Resume Match tab.

## Project Structure

```text
jobtrack/
├── backend/
│   ├── main.py          # API routes and app startup
│   ├── crud.py          # Database reads and writes, stats, follow-ups, agent runs
│   ├── resume_agent.py  # Resume Match agent (pure Python, no database code)
│   ├── default_profile.py  # Starting resume profile
│   ├── models.py        # SQLAlchemy tables: applications, resume_profile
│   ├── schemas.py       # Pydantic request and response models
│   ├── database.py      # Database connection and sessions
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── manifest.json    # Lets phones add the app to the home screen
├── docs/
│   └── FIND_JOBS_SPEC.md  # Spec for the next feature (not built yet)
├── .env.example       # Job-search API keys template (copy to .env)
├── start-for-phone.bat  # Runs the server so a phone can open it
├── CLAUDE.md          # Project notes for Claude Code
└── README.md
```
