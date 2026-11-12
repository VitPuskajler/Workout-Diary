"""Download the live database from PythonAnywhere (GET /api/backup/db).

One-time setup
  1. On PythonAnywhere (Bash console, in the project folder):
         python tools/download_db.py --new-token
     This writes instance/backup_token and prints the token. Then reload the
     web app.
  2. On this computer, put the same token in instance/backup_token
     (or in the WORKOUT_BACKUP_TOKEN environment variable).

Use
    python tools/download_db.py             # saves instance/backups/workout-pa-<time>.db
    python tools/download_db.py --replace   # also makes it the local instance/workout.db
                                            # (the current local DB is copied aside first)
    python tools/download_db.py --url http://127.0.0.1:5000   # another server

Only the standard library is used, so no virtualenv is needed.
"""
import argparse
import os
import secrets
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE = os.path.join(ROOT, "instance")
TOKEN_PATH = os.path.join(INSTANCE, "backup_token")
LOCAL_DB = os.path.join(INSTANCE, "workout.db")
BACKUP_DIR = os.path.join(INSTANCE, "backups")
DEFAULT_URL = "https://vito.pythonanywhere.com"


def new_token():
    if os.path.exists(TOKEN_PATH):
        answer = input(f"{TOKEN_PATH} already exists. Replace it? [y/N] ")
        if answer.strip().lower() != "y":
            sys.exit("Kept the old token.")
    token = secrets.token_urlsafe(32)
    os.makedirs(INSTANCE, exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as handle:
        handle.write(token)
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
    print(f"Token written to {TOKEN_PATH}:\n\n    {token}\n")
    print("Reload the web app, then put the same token in instance/backup_token on your computer.")


def read_token():
    token = os.environ.get("WORKOUT_BACKUP_TOKEN", "").strip()
    if not token and os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as handle:
            token = handle.read().strip()
    if not token:
        sys.exit(f"No token: put it in {TOKEN_PATH} or set WORKOUT_BACKUP_TOKEN.")
    return token


def download(url, token):
    request = urllib.request.Request(
        url.rstrip("/") + "/api/backup/db",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "workout-diary-backup"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            sys.exit("404: wrong token, or the server has no token / is not running this code yet.")
        sys.exit(f"Server answered {error.code} {error.reason}.")
    except urllib.error.URLError as error:
        sys.exit(f"Could not reach {url}: {error.reason}")


def check_sqlite(path):
    """Make sure what arrived is a real, intact SQLite database."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
    except sqlite3.DatabaseError as error:
        sys.exit(f"The download is not a usable database ({error}); kept at {path}")
    if result != "ok":
        sys.exit(f"Integrity check failed ({result}); kept at {path}")
    return users, sessions


def main():
    parser = argparse.ArgumentParser(description="Download the live Workout Diary database.")
    parser.add_argument("--new-token", action="store_true",
                        help="create instance/backup_token (run this on the server)")
    parser.add_argument("--replace", action="store_true",
                        help="also replace the local instance/workout.db")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"server address (default {DEFAULT_URL})")
    args = parser.parse_args()

    if args.new_token:
        new_token()
        return

    data = download(args.url, read_token())
    stamp = f"{datetime.now():%Y%m%d-%H%M%S}"
    os.makedirs(BACKUP_DIR, exist_ok=True)
    saved = os.path.join(BACKUP_DIR, f"workout-pa-{stamp}.db")
    with open(saved, "wb") as handle:
        handle.write(data)
    users, sessions = check_sqlite(saved)
    print(f"Downloaded {len(data) / 1024:.0f} KB ({users} users, {sessions} sessions) -> {saved}")

    if args.replace:
        if os.path.exists(LOCAL_DB):
            aside = os.path.join(BACKUP_DIR, f"workout-local-{stamp}.db")
            shutil.copy2(LOCAL_DB, aside)
            print(f"Old local database copied to {aside}")
        shutil.copy2(saved, LOCAL_DB)
        print(f"{LOCAL_DB} is now the downloaded copy.")


if __name__ == "__main__":
    main()
