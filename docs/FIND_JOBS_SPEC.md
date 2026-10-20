# Find Jobs: implementation spec

Read `CLAUDE.md` first. Its rules still apply, except where this spec allows otherwise.

## Goal

Add a **Find Jobs** tab. You enter a role and a location, the app searches free,
permitted job-search APIs, and every result is scored by the existing Resume Match
agent (`backend/resume_agent.py`), best match first. You can save any result to the
tracker. A **Paste job** form covers jobs you find on LinkedIn or Naukri.

```
Enter role + location ─► Search job APIs ─► Score every job ─► Ranked results ─► Save to tracker
                                                ▲                                     (Wishlist)
                         Paste a job ───────────┘                                         │
                         (LinkedIn / Naukri)                                              ▼
           Follow-up reminder ◄── Mark as Applied ◄── Apply on the original posting ◄─────┘
```

## Hard rules

1. **Never scrape LinkedIn, Naukri, Indeed or any site that forbids it.** Only use the four
   official APIs below. LinkedIn and Naukri jobs come in only through Paste job, where
   the user copies the text themselves.
2. **No new packages.** Make HTTP calls with the standard library (`urllib.request`,
   `json`, `html`, `os`). Do not add `requests`, `httpx`, `python-dotenv` or anything else
   to `requirements.txt`.
3. **Keys never go in code or Git.** Read them from a `.env` file, which `.gitignore`
   already excludes. Commit `.env.example` with empty values only.
4. A missing key or a failing source must **not** break the search. Skip that source and
   report it in the response's `warnings` list.
5. Every source call has a **10-second timeout** and is wrapped in `try/except`.
6. Keep the code readable for an interview: short functions, comments that explain *why*.

## Configuration

Create `backend/config.py`. It loads `.env` with a tiny parser of its own (no packages):
read `KEY=value` lines, skip blank lines and lines starting with `#`, and strip quotes.
Real environment variables win over the file. Settings:

| Setting | Meaning | Default |
| --- | --- | --- |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Adzuna developer credentials | empty → Adzuna skipped |
| `ADZUNA_COUNTRY` | Adzuna country code | `in` |
| `JOOBLE_API_KEY` | Jooble key | empty → Jooble skipped |
| `GREENHOUSE_BOARDS` | Comma-separated board tokens, e.g. `companya,companyb` | empty |
| `LEVER_COMPANIES` | Comma-separated Lever company slugs | empty |

Create `.env.example` at the project root with these keys and empty values.

## Sources (`backend/job_sources.py`)

Every source returns a list of the **same job dict**, so the rest of the app never
needs to know where a job came from:

```python
{
    "source": "Adzuna",          # Adzuna | Jooble | Greenhouse | Lever
    "external_id": "12345",      # the source's own id, as a string
    "title": "Python Developer",
    "company": "Acme",
    "location": "Chennai",
    "url": "https://...",        # where the user applies
    "description": "plain text", # HTML stripped, whitespace collapsed
    "posted": "2026-10-18",      # ISO date if the source gives one, else None
}
```

Write a helper `fetch_json(url, method="GET", body=None)` that sets a `User-Agent`
header, sends JSON when `body` is given, applies the 10-second timeout and returns
the parsed JSON. Write `clean_text(html_text)`: `html.unescape`, remove tags with a
regex, collapse whitespace.

Field mappings below are from each API's public documentation. **Before you code each
source, make one real request and check the actual response shape.** If a field
differs, follow the real response and mention it in your summary.

### Adzuna (needs a free key)
- `GET https://api.adzuna.com/v1/api/jobs/{country}/search/1?app_id=…&app_key=…&what={role}&where={location}&results_per_page=20&content-type=application/json`
- `results[]`: `title`, `company.display_name`, `location.display_name`,
  `redirect_url`, `description` (a shortened excerpt), `created`, `id`.

### Jooble (needs a free key)
- `POST https://jooble.org/api/{key}` with body `{"keywords": role, "location": location}`.
- `jobs[]`: `title`, `company`, `location`, `link`, `snippet` (shortened, may contain
  HTML), `updated`, `id`.

### Greenhouse job boards (no key)
- For each token: `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
- `jobs[]`: `id`, `title`, `location.name`, `absolute_url`, `content` (HTML-escaped,
  so unescape then strip tags), `updated_at`.
- Company name: the token in title case, unless the response gives a better one.
- These boards return **all** of a company's jobs: keep only jobs whose title contains
  any word of the role (case-insensitive) and, if a location was given, whose location
  contains it or says "Remote".

### Lever postings (no key)
- For each slug: `GET https://api.lever.co/v0/postings/{slug}?mode=json`
- Returns a list: `id`, `text` (the title), `categories.location`, `hostedUrl`,
  `descriptionPlain`, `createdAt` (milliseconds since 1970).
- Filter by role and location the same way as Greenhouse.

### Combining results
- Call each configured source in turn and collect warnings for any that are skipped
  or fail.
- Remove duplicates: same `url`, or the same lower-cased `title` + `company`.
- Score each job with `resume_agent.analyze(job["description"], profile)` and attach
  `match_score`, `matched_skills`, `missing_skills`.
- Sort by `match_score`, highest first, and return at most 50.
- Mark jobs that are already saved in the tracker (match on `job_link`) with
  `already_saved: true`.

## Database changes

- Add `source` (String) and `external_id` (String) columns to `Application`.
  Add both to `add_missing_columns()` in `database.py` as well (see `CLAUDE.md`).
- Moving an application from *Wishlist* to *Applied* in `crud.update_application`: if
  the request did not also send `applied_date` / `follow_up_date`, set `applied_date`
  to today and `follow_up_date` to today + 7 days. A job saved weeks ago and applied to
  today must get today's date and a fresh reminder.

## API endpoints (`backend/main.py`)

Declare fixed paths before any `/{id}` path, as `CLAUDE.md` says.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/jobs/search?role=&location=` | Search all configured sources, score and rank. `role` is required (2–100 chars), `location` optional. Returns `{"jobs": [...], "warnings": [...], "sources_used": [...]}` |
| GET | `/api/jobs/sources` | Which sources are configured: `[{"name": "Adzuna", "ready": true}, …]`. Never return the keys themselves |
| POST | `/api/jobs/save` | Body = one job dict from search. Re-runs the Resume Match agent on its description, then creates an Application with status **Wishlist**, `job_link` = url, and the description, score, summary, source and external_id. If an application with the same `job_link` exists → **409** "Already in your tracker" |
| POST | `/api/jobs/paste` | Body: `job_description` (required, ≥ 20 chars), `company` (required), `role` (optional; if empty use `resume_agent.find_job_title`, else "Unknown role"), `location`, `job_link` (optional, must start with http/https). Same save as above with `source` = "Pasted". Returns the new application |

Add Pydantic models for these in `schemas.py`: `JobResult`, `JobSearchResponse`,
`JobSave`, `JobPaste`. Run the profile + scoring through `crud.py`, so the routes stay thin.

## Frontend

Add a third tab, **Find Jobs**, using the existing tab pattern in `index.html` and `app.js`.

- **Search form:** role (required), location (default "Chennai"), Search button. While
  searching, disable the button and show "Searching…".
- **Source status line** from `/api/jobs/sources`, e.g. "Adzuna ✓ · Jooble – add a key
  in .env". Show any `warnings` from the search in the existing banner style.
- **Result cards**, best match first: title, company · location · source, a match-score
  badge (green ≥ 70, amber 40–69, grey < 40), up to 5 matched skills as chips, and a
  "Skills to review" line. Buttons: **Open** (new tab, `rel="noopener"`) and **Save**.
  After saving, the button becomes "Saved ✓" and is disabled; `already_saved` jobs start
  that way.
- **Note on every card:** "Score is based on a shortened description. Paste the full job
  description in Resume Match for an exact score."
- **Paste job** (a collapsible `<details>` under the search): link, company, role,
  location, description, and a **Save to tracker** button. After saving, show a link to
  the Applications tab.
- Empty states: "No jobs found. Try a broader role, or another location." and, when no
  source is configured, "Add an Adzuna or Jooble key to .env, or list companies in
  GREENHOUSE_BOARDS / LEVER_COMPANIES."
- Insert all API text with `textContent`, never `innerHTML` (job text comes from outside).
- It must work at phone width (390 px), like the other tabs.

## Docs to update

- `README.md`: the Find Jobs feature, the new endpoints, the sources and their limits,
  how to get the keys, and a short **"Why no LinkedIn or Naukri scraping"** note (their
  terms forbid automated access; Paste job covers them).
- `CLAUDE.md`: add `job_sources.py` and `config.py` to Layout; add rules: "HTTP calls use
  urllib only", "keys come from .env, never from code", "never scrape sites that forbid it".

## Testing (show a pass/fail table at the end)

Use FastAPI's `TestClient`. **Mock the network** by patching `fetch_json`, so tests don't
depend on keys or the internet; then do one live check per configured source.

1. No keys and no boards configured → search returns `jobs: []` and a helpful warning, status 200.
2. Mocked Adzuna, Jooble, Greenhouse and Lever responses → one combined list, HTML stripped,
   duplicates removed, sorted by `match_score`.
3. One source raises a timeout → the other sources' results still return, plus a warning.
4. Greenhouse/Lever filtering keeps only matching titles and locations.
5. Save a job → appears in `/api/applications` as Wishlist with score and summary; saving
   it again → 409.
6. Paste job with no role → the role comes from a `Job Title:` line; missing company → 422;
   bad link → 422.
7. Change a saved job from Wishlist to Applied → `applied_date` = today, follow-up = today + 7.
8. An existing `jobtrack.db` without the new columns upgrades on startup and keeps its data.
9. `/api/jobs/sources` never contains a key value.
10. In the browser at phone width: search, save, paste and the tab switch all work, with no
    console errors.

## Out of scope (ask before doing any of these)

New packages, login, scheduled background searches, sending emails, using an LLM, or any
other job source.
