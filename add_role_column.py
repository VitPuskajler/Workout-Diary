"""One-off migration: give users a role, and make Vito the admin.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

Safe to run twice; it checks before it changes anything.

    python add_role_column.py
"""
import os
import sqlite3
import sys

ADMIN_USERNAME = "Vito"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "instance", "workout.db")


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(users)")]

        if "role" in columns:
            print("role column already present - nothing to add")
        else:
            conn.execute(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) "
                "NOT NULL DEFAULT 'user'"
            )
            print("role column added, every existing user defaulted to 'user'")

        cursor = conn.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?", (ADMIN_USERNAME,)
        )
        if cursor.rowcount:
            print(f"{ADMIN_USERNAME} is now admin")
        else:
            print(f"WARNING: no user called {ADMIN_USERNAME} in this database")

        conn.commit()

        print("\ncurrent roles:")
        for user_id, username, role in conn.execute(
            "SELECT user_id, username, role FROM users ORDER BY user_id"
        ):
            print(f"  {user_id}  {username:12} {role}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
