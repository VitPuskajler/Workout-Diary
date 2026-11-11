"""One-off migration: the creatine_intakes table behind the Creatine switch
on /body (Body Diary) - one row per user per day creatine was taken.

Locally `python server.py` creates it on its own (db.create_all()), but the
app on PythonAnywhere never runs that - so run this there BEFORE reloading
the app, or /body fails. No other table is touched. Matches CreatineIntake
in models/models.py.

Safe to run twice.

    python temp/add_creatine_table.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        if conn.execute("PRAGMA table_info(creatine_intakes)").fetchall():
            print("creatine_intakes table already present")
            return
        conn.execute("""CREATE TABLE creatine_intakes (
\tcreatine_intake_id INTEGER NOT NULL,
\tuser_id INTEGER NOT NULL,
\ttaken_on DATE NOT NULL,
\tPRIMARY KEY (creatine_intake_id),
\tUNIQUE (user_id, taken_on),
\tFOREIGN KEY(user_id) REFERENCES users (user_id)
)""")
        conn.execute("CREATE INDEX ix_creatine_intakes_user_id ON creatine_intakes (user_id)")
        conn.commit()
        print("creatine_intakes table created")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
