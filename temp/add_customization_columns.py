"""One-off migration: the Customization switches on /profile.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

  - users.show_session_icons (0/1, 1)     the exercise's icon in each row of
                                          the training session table
  - users.animate_session_icons (0/1, 0)  those icons play their rep
  - users.show_stopwatch (0/1, 1)         the stopwatch bar on the training pages
  - users.show_set_gaps (0/1, 1)          "+2:35" since the previous set
  - users.language ("en")                 "en", "sk" or "cs" (translations/i18n.py)
  - sessions.started_by_stopwatch (NULL)  whether the duration runs from a
                                          Start tap; NULL for older sessions
  - exercise_entries.superset_of (NULL)   the set a superset set was done
                                          straight after (the SS button)

Existing users get the defaults: icons on, not moving, stopwatch and set gaps
on - how the app looked before the switches existed.

Safe to run twice; it checks before it changes anything.

    python temp/add_customization_columns.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

# (table, column, SQL type and default)
COLUMNS = [
    ("users", "show_session_icons", "BOOLEAN NOT NULL DEFAULT 1"),
    ("users", "animate_session_icons", "BOOLEAN NOT NULL DEFAULT 0"),
    ("users", "show_stopwatch", "BOOLEAN NOT NULL DEFAULT 1"),
    ("users", "show_set_gaps", "BOOLEAN NOT NULL DEFAULT 1"),
    ("users", "language", "VARCHAR(5) NOT NULL DEFAULT 'en'"),
    ("sessions", "started_by_stopwatch", "BOOLEAN"),
    ("exercise_entries", "superset_of", "INTEGER REFERENCES exercise_entries(entry_id)"),
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
