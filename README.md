# JobTrack

A mobile-friendly web app for tracking job applications: log every application,
move it through each stage, get reminded to follow up, and see how the search is going.

## Features

- Add, view, edit and delete job applications
- Track each application through five stages: Wishlist, Applied, Interview, Offer, Rejected
- Automatic follow-up reminder 7 days after applying (or a date you choose)
- Dashboard with totals, interviews, offers and response rate
- Search by company or role, and filter by status
- Works on a phone and can be added to the home screen like an app

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy ORM, SQLite, Pydantic
- **Frontend:** HTML, CSS, JavaScript (no framework)

## Run It

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
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

## How It Works

- **Validation** happens twice: Pydantic checks every request (required fields,
  allowed statuses, link format), and the database has a check constraint so an
  invalid status can never be saved.
- **Response rate** = applications that got a reply (Interview, Offer or Rejected)
  ÷ applications sent (everything except Wishlist).
- **Stats** use one SQL `GROUP BY` query instead of loading every row into Python.
- **Follow-ups** are applications still in "Applied" whose follow-up date is today or earlier.

## Project Structure

```text
jobtrack/
├── backend/
│   ├── main.py          # API routes and app startup
│   ├── crud.py          # Database reads and writes, stats, follow-ups
│   ├── models.py        # SQLAlchemy table definition
│   ├── schemas.py       # Pydantic request and response models
│   └── database.py      # Database connection and sessions
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── manifest.json    # Lets phones add the app to the home screen
├── requirements.txt
├── start-for-phone.bat  # Runs the server so a phone can open it
├── CLAUDE.md          # Project notes for Claude Code
└── README.md
```
