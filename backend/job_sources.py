"""
Job search sources: Adzuna, Jooble, Greenhouse job boards and Lever postings.

Only official, public APIs are used. LinkedIn, Naukri and Indeed forbid automated
access, so their jobs come in through the Paste job form instead.

Every source returns the same job dict (see make_job), so the rest of the app
never needs to know where a job came from.
"""

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TIMEOUT_SECONDS = 10
USER_AGENT = "JobTrack/1.0 (personal job tracker)"
# Plenty for skill matching, and keeps one huge posting from bloating the response.
MAX_DESCRIPTION_CHARS = 20000
TAG_PATTERN = re.compile(r"<[^>]+>")


# ---------- Helpers ----------

def fetch_json(url: str, method: str = "GET", body: dict | None = None):
    """Call a JSON API with the standard library (no extra packages) and a 10-second timeout."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(html_text: str | None) -> str:
    """Turn HTML (even escaped HTML) into plain text on one line."""
    text = html.unescape(html_text or "")
    text = TAG_PATTERN.sub(" ", text)
    # Unescape again: escaped HTML like &lt;p&gt;Tom &amp;amp; Co becomes "Tom &amp; Co" after one pass.
    return " ".join(html.unescape(text).split())


def make_job(source, external_id, title, company, location, url, description, posted) -> dict:
    return {
        "source": source,
        "external_id": str(external_id),
        "title": clean_text(title),
        "company": clean_text(company) or "Unknown company",
        "location": clean_text(location),
        "url": url,
        "description": clean_text(description)[:MAX_DESCRIPTION_CHARS],
        "posted": posted,
    }


def is_usable(job: dict) -> bool:
    """Skip jobs without a title or a normal web link, so one bad entry can't break the results."""
    return bool(job["title"]) and (job["url"] or "").startswith(("http://", "https://"))


def iso_date(value: str | None) -> str | None:
    """'2026-10-18T09:30:00Z' -> '2026-10-18'. The first 10 characters are the date."""
    return value[:10] if value else None


def matches_role(title: str, role: str) -> bool:
    """Company boards list every job they have, so keep only titles that share a word with the role."""
    title = title.lower()
    return any(word in title for word in role.lower().split())


def matches_location(job_location: str, location: str, remote: bool = False) -> bool:
    if not location:
        return True
    job_location = job_location.lower()
    return remote or location.lower() in job_location or "remote" in job_location


def describe_error(error: Exception) -> str:
    """A short reason for the warning. Never include the URL, which can contain a key."""
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, urllib.error.URLError):
        return str(error.reason)
    return str(error) or type(error).__name__


# ---------- Sources ----------

def fetch_adzuna(role: str, location: str, settings: dict) -> list[dict]:
    params = {
        "app_id": settings["adzuna_app_id"],
        "app_key": settings["adzuna_app_key"],
        "what": role,
        "results_per_page": 20,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location
    country = settings["adzuna_country"]
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?" + urllib.parse.urlencode(params)

    return [
        make_job(
            "Adzuna", item.get("id"), item.get("title"),
            (item.get("company") or {}).get("display_name"),
            (item.get("location") or {}).get("display_name"),
            item.get("redirect_url"), item.get("description"), iso_date(item.get("created")),
        )
        for item in fetch_json(url).get("results", [])
    ]


def fetch_jooble(role: str, location: str, settings: dict) -> list[dict]:
    url = "https://jooble.org/api/" + urllib.parse.quote(settings["jooble_api_key"])
    data = fetch_json(url, method="POST", body={"keywords": role, "location": location})
    return [
        make_job(
            "Jooble", item.get("id"), item.get("title"), item.get("company"),
            item.get("location"), item.get("link"), item.get("snippet"), iso_date(item.get("updated")),
        )
        for item in data.get("jobs", [])
    ]


def fetch_greenhouse(board: str, role: str, location: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(board)}/jobs?content=true"
    jobs = []
    for item in fetch_json(url).get("jobs", []):
        title = item.get("title") or ""
        job_location = (item.get("location") or {}).get("name") or ""
        if not (matches_role(title, role) and matches_location(job_location, location)):
            continue
        jobs.append(make_job(
            "Greenhouse", item.get("id"), title,
            # The real response includes company_name; the board token is only a fallback.
            item.get("company_name") or board.title(),
            job_location, item.get("absolute_url"), item.get("content"), iso_date(item.get("updated_at")),
        ))
    return jobs


def fetch_lever(company: str, role: str, location: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{urllib.parse.quote(company)}?mode=json"
    jobs = []
    for item in fetch_json(url):
        title = item.get("text") or ""
        job_location = (item.get("categories") or {}).get("location") or ""
        # Lever marks remote jobs in workplaceType, not always in the location text.
        remote = item.get("workplaceType") == "remote"
        if not (matches_role(title, role) and matches_location(job_location, location, remote)):
            continue
        created = item.get("createdAt")
        # createdAt is milliseconds since 1970.
        posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).date().isoformat() if created else None
        jobs.append(make_job(
            "Lever", item.get("id"), title, company.title(),
            job_location, item.get("hostedUrl"), item.get("descriptionPlain"), posted,
        ))
    return jobs


# ---------- Combining ----------

def source_status(settings: dict) -> list[dict]:
    """Which sources can run. Only true/false, never the keys themselves."""
    return [
        {"name": "Adzuna", "ready": bool(settings["adzuna_app_id"] and settings["adzuna_app_key"])},
        {"name": "Jooble", "ready": bool(settings["jooble_api_key"])},
        {"name": "Greenhouse", "ready": bool(settings["greenhouse_boards"])},
        {"name": "Lever", "ready": bool(settings["lever_companies"])},
    ]


def planned_calls(role: str, location: str, settings: dict) -> list[tuple]:
    """One (label, function) pair per API call: one per key-based source, one per company board."""
    calls = []
    if settings["adzuna_app_id"] and settings["adzuna_app_key"]:
        calls.append(("Adzuna", lambda: fetch_adzuna(role, location, settings)))
    if settings["jooble_api_key"]:
        calls.append(("Jooble", lambda: fetch_jooble(role, location, settings)))
    for board in settings["greenhouse_boards"]:
        calls.append((f"Greenhouse ({board})", lambda board=board: fetch_greenhouse(board, role, location)))
    for company in settings["lever_companies"]:
        calls.append((f"Lever ({company})", lambda company=company: fetch_lever(company, role, location)))
    return calls


def remove_duplicates(jobs: list[dict]) -> list[dict]:
    """The same job is often listed on several sites: same link, or same title at the same company."""
    seen = set()
    unique = []
    for job in jobs:
        keys = {job["url"], (job["title"].lower(), job["company"].lower())}
        if keys & seen:
            continue
        seen |= keys
        unique.append(job)
    return unique


def search_all(role: str, location: str, settings: dict) -> dict:
    """Call every configured source in turn. A failing source becomes a warning, not an error."""
    jobs, warnings, sources_used = [], [], []

    for status in source_status(settings):
        if not status["ready"]:
            warnings.append(f"{status['name']} skipped: not set up in .env.")

    calls = planned_calls(role, location, settings)
    if not calls:
        warnings = [
            "No job sources are set up. Add an Adzuna or Jooble key to .env, "
            "or list companies in GREENHOUSE_BOARDS / LEVER_COMPANIES."
        ]

    for label, call in calls:
        try:
            jobs.extend(job for job in call() if is_usable(job))
            sources_used.append(label)
        except Exception as error:  # Any failure in one source must not stop the others.
            warnings.append(f"{label} failed: {describe_error(error)}")

    return {"jobs": remove_duplicates(jobs), "warnings": warnings, "sources_used": sources_used}
