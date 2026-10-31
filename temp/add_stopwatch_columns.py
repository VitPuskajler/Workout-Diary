"""One-off migration: timestamps for the training stopwatch.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

Adds exercise_entries.logged_at (when a set was logged) and
exercise_entries.started_at (when the "Set" button was tapped, optional). Both
are naive UTC and NULL for every set logged before the stopwatch existed.

Safe to run twice; it checks before it changes anything.

    python temp/add_stopwatch_columns.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

NEW_COLUMNS = ["logged_at", "started_at"]


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(exercise_entries)")]

        for name in NEW_COLUMNS:
            if name in columns:
                print(f"{name} column already present - nothing to add")
            else:
                conn.execute(f"ALTER TABLE exercise_entries ADD COLUMN {name} DATETIME")
                print(f"{name} column added")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
