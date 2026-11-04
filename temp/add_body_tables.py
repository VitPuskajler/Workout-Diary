"""One-off migration: the two tables behind /body (Body measurement).

  - body_weights        one weight (kg) per user per day, with how it was
                        weighed: time_of_day, weighed_at, fasted, after_bowel
  - body_measurements   tape measurements (cm) and body fat (%) per user per day

Locally `python server.py` creates the tables on its own (db.create_all()),
but the app on PythonAnywhere never runs that - so run this there BEFORE
reloading the app, or /body fails. It also adds any of the columns below a
table lacks (body_weights was created before its four weighing columns).
No other table is touched.

Plain sqlite3, like the other migrations here: any Python runs it, no
virtualenv needed. The tables match what db.create_all() makes from
models/models.py (BodyWeight, BodyMeasurement).

Safe to run twice; it only creates what is missing.

    python temp/add_body_tables.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

MEASUREMENTS = ["neck", "shoulders", "chest", "waist", "hips",
                "biceps_left", "biceps_right", "thigh_left", "thigh_right",
                "calf_left", "calf_right", "body_fat"]

# table -> (key column, [(column, definition)] after user_id)
TABLES = {
    "body_weights": ("body_weight_id", [
        ("measured_on", "DATE NOT NULL"),
        ("weight", "FLOAT NOT NULL"),
        ("time_of_day", "VARCHAR(10)"),
        ("weighed_at", "VARCHAR(5)"),
        ("fasted", "BOOLEAN"),
        ("after_bowel", "BOOLEAN"),
    ]),
    "body_measurements": ("body_measurement_id",
                          [("measured_on", "DATE NOT NULL")]
                          + [(name, "FLOAT") for name in MEASUREMENTS]),
}


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        for table, (key, columns) in TABLES.items():
            present = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            if not present:
                body = ",\n\t".join(
                    [f"{key} INTEGER NOT NULL", "user_id INTEGER NOT NULL"]
                    + [f"{name} {definition}" for name, definition in columns]
                    + [f"PRIMARY KEY ({key})", "UNIQUE (user_id, measured_on)",
                       "FOREIGN KEY(user_id) REFERENCES users (user_id)"])
                conn.execute(f"CREATE TABLE {table} (\n\t{body}\n)")
                conn.execute(f"CREATE INDEX ix_{table}_user_id ON {table} (user_id)")
                print(f"{table} table created")
                continue
            print(f"{table} table already present")
            for name, definition in columns:
                if name in present:
                    continue
                if "NOT NULL" in definition:
                    sys.exit(f"{table}.{name} is NOT NULL - add it by hand")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
                print(f"  {table}.{name} column added ({definition})")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
