"""
Settings for the job-search sources, read from a .env file at the project root.

A tiny parser instead of python-dotenv, so the project needs no extra package.
Keys live only in .env (ignored by Git), never in the code.
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Read KEY=value lines, skipping blank lines and # comments."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_settings() -> dict:
    """Read the settings fresh each time, so editing .env needs no server restart."""
    file_values = read_env_file()

    def setting(name: str, default: str = "") -> str:
        # A real environment variable wins over the file, so a server can be configured without one.
        return os.environ.get(name) or file_values.get(name) or default

    return {
        "adzuna_app_id": setting("ADZUNA_APP_ID"),
        "adzuna_app_key": setting("ADZUNA_APP_KEY"),
        "adzuna_country": setting("ADZUNA_COUNTRY", "in"),
        "jooble_api_key": setting("JOOBLE_API_KEY"),
        "greenhouse_boards": split_list(setting("GREENHOUSE_BOARDS")),
        "lever_companies": split_list(setting("LEVER_COMPANIES")),
    }
