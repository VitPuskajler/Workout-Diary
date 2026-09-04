"""One-off migration: give users an "is_approved" flag for manual registration
approval.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

Every account that already exists predates this feature and should not
suddenly be locked out, so existing rows are backfilled to approved (1).
Only the column's own default (0) applies to whoever registers after this -
they sit pending until an admin approves them from /profile.

Safe to run twice; it checks before it changes anything.

    python add_approval_column.py
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
        columns = [row[1] for row in conn.execute("PRAGMA table_info(users)")]

        if "is_approved" in columns:
            print("is_approved column already present - nothing to add")
        else:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 0"
            )
            conn.execute("UPDATE users SET is_approved = 1")
            conn.commit()
            print("is_approved column added, every existing user backfilled to approved")

        counts = conn.execute(
            "SELECT is_approved, COUNT(*) FROM users GROUP BY is_approved"
        ).fetchall()
        print("\ncurrent approval breakdown:")
        for approved, count in counts:
            label = "approved" if approved else "pending"
            print(f"  {label:8} {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
