"""One-off migration: give exercise_entries a weight unit ("kg" / "lbs" / "other").

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

Every weight logged before this migration was entered assuming kilograms
(the app's only unit until now), so existing rows are backfilled to "kg" -
no conversion needed, they already are kg.

Safe to run twice; it checks before it changes anything.

    python add_unit_column.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "instance", "workout.db")


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(exercise_entries)")]

        if "unit" in columns:
            print("unit column already present - nothing to add")
        else:
            conn.execute(
                "ALTER TABLE exercise_entries ADD COLUMN unit VARCHAR(10) "
                "NOT NULL DEFAULT 'kg'"
            )
            conn.commit()
            print("unit column added, every existing entry defaulted to 'kg'")

        counts = conn.execute(
            "SELECT unit, COUNT(*) FROM exercise_entries GROUP BY unit"
        ).fetchall()
        print("\ncurrent unit breakdown:")
        for unit, count in counts:
            print(f"  {unit:6} {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
