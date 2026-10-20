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
- **Find Jobs:** search job APIs by role and location, see every result scored against
  your resume (best match first), and save any job to your Wishlist in one tap.
  **Paste job** saves jobs you find on LinkedIn, Naukri or anywhere else
- Moving a saved job from Wishlist to Applied sets today's date and a fresh follow-up reminder
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
| GET | `/api/jobs/search?role=&location=` | Search all configured job sources, scored and ranked |
| GET | `/api/jobs/sources` | Which job sources are set up (never returns the keys) |
| POST | `/api/jobs/save` | Save a search result to the Wishlist (409 if already saved) |
| POST | `/api/jobs/paste` | Save a job pasted by hand (role read from a `Job Title:` line if empty) |

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

## Find Jobs

Enter a role and a location. The app asks each configured job source, removes
duplicates (same link, or same title at the same company), scores every job with the
Resume Match agent and shows the best matches first (up to 50). Jobs already in the
tracker are marked as saved.

| Source | Key needed | Limits |
| --- | --- | --- |
| [Adzuna](https://developer.adzuna.com) | Free app id + key | 20 results per search; descriptions are shortened excerpts |
| Jooble (request a key on jooble.org's API page) | Free key | Descriptions are short snippets |
| Greenhouse job boards | None | Only the companies you list; their whole board is filtered by role and location |
| Lever postings | None | Same as Greenhouse |

Because Adzuna and Jooble only return excerpts, the score on a search result is a
first guess. Paste the full description into Resume Match for an exact score.

**Setting up the keys:** copy `.env.example` to `.env` and fill in what you have.
Leave a value empty to skip that source. For company boards, use the name in the
board's address: `boards.greenhouse.io/<token>` or `jobs.lever.co/<slug>`.

```text
ADZUNA_APP_ID=your-id
ADZUNA_APP_KEY=your-key
GREENHOUSE_BOARDS=gitlab,stripe
```

`.env` is in `.gitignore`, so keys never reach GitHub. Changes to `.env` apply on the
next search, with no restart. A missing key, a slow source (10-second timeout) or a
failing source never breaks the search: it is skipped and named in a warning.

### Why no LinkedIn or Naukri scraping

LinkedIn's and Naukri's terms forbid automated access to their sites, so JobTrack never
reads them. It only uses official, public job APIs. For jobs on those sites, copy the
description into **Paste job** and it gets the same score and Wishlist entry.

## Project Structure

```text
jobtrack/
├── backend/
│   ├── main.py          # API routes and app startup
│   ├── crud.py          # Database reads and writes, stats, follow-ups, agent runs, job search
│   ├── resume_agent.py  # Resume Match agent (pure Python, no database code)
│   ├── job_sources.py   # Adzuna, Jooble, Greenhouse and Lever API calls (urllib only)
│   ├── config.py        # Reads job-search keys from .env
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
│   └── FIND_JOBS_SPEC.md  # Spec the Find Jobs feature was built from
├── .env.example       # Job-search API keys template (copy to .env)
├── start-for-phone.bat  # Runs the server so a phone can open it
├── CLAUDE.md          # Project notes for Claude Code
└── README.md
```
