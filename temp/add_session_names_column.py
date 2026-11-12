"""One-off migration: the "Exercise names in training session" switch in
Customization.

db.create_all() never adds a column to an existing table, so this has to be
run by hand, once per database: locally, and again on PythonAnywhere BEFORE
reloading the app (every page that loads the user fails without it).

  - users.show_session_names (0/1, 1)   the names in the exercise table
                                        under the set log on Training
                                        Session - on, as everybody had them

Safe to run twice; it checks before it changes anything.

    python temp/add_session_names_column.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

COLUMNS = [
    ("users", "show_session_names", "BOOLEAN NOT NULL DEFAULT 1"),
]


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        for table, name, definition in COLUMNS:
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            if name in columns:
                print(f"{table}.{name} column already present - nothing to add")
            else:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
                print(f"{table}.{name} column added ({definition})")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
