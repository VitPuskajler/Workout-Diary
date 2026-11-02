"""One-off migration: User activity on the admin's User management page.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere (before the new code runs
there - every page that loads the user fails without the columns).

  - users.last_login_at (NULL)   when the login form last let the user in (UTC)
  - users.last_seen_at  (NULL)   when the user last opened any page (UTC)

Existing users start with NULL - "never" until they next come.

Safe to run twice; it checks before it changes anything.

    python temp/add_activity_columns.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

COLUMNS = [
    ("users", "last_login_at", "DATETIME"),
    ("users", "last_seen_at", "DATETIME"),
]


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    try:
        for table, column, sql_type in COLUMNS:
            existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
            if column in existing:
                print(f"{table}.{column}: already there")
                continue
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            print(f"{table}.{column}: added")
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    main()
