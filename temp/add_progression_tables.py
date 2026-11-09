"""One-off migration: progression ladders.

  - creates the tables progressions and progression_levels (if missing)
  - fills in the ladders in LADDERS: each level points at an exercise that is
    already in the catalog (temp/add_front_lever_progressions.py adds the
    front lever ones - run it first)

A ladder already there is left as it is, so a level, label or goal changed on
/admin/exercises since is kept. An exercise missing from the catalog, or
already a level of another ladder, is reported and skipped.

Safe to run twice. Plain sqlite3, like the other scripts here. Without --apply
it only prints what it would do. With --apply it first copies the database to
instance/workout.db.bak-<timestamp>, then makes the changes in one
transaction.

    python temp/add_progression_tables.py            # dry run
    python temp/add_progression_tables.py --apply    # make the changes
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

TABLES = {
    "progressions": """
        CREATE TABLE progressions (
            progression_id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            name_sk VARCHAR(100),
            name_cs VARCHAR(100)
        )""",
    "progression_levels": """
        CREATE TABLE progression_levels (
            progression_level_id INTEGER NOT NULL PRIMARY KEY,
            progression_id INTEGER NOT NULL REFERENCES progressions (progression_id),
            exercise_id INTEGER NOT NULL UNIQUE REFERENCES exercises (exercise_id),
            level INTEGER NOT NULL,
            label VARCHAR(60) NOT NULL,
            label_sk VARCHAR(60),
            label_cs VARCHAR(60),
            goal_sets INTEGER,
            goal_value INTEGER,
            UNIQUE (progression_id, level)
        )""",
}
INDEXES = ["CREATE INDEX IF NOT EXISTS ix_progression_levels_progression_id "
           "ON progression_levels (progression_id)"]

# The front lever rungs, shared by both ladders: (label, sk, cs)
LEVER_RUNGS = [
    ("Tuck", "Skrčenie", "Skrčení"),
    ("Advanced Tuck", "Pokročilé skrčenie", "Pokročilé skrčení"),
    ("One Leg", "Jedna noha", "Jedna noha"),
    ("Straddle", "Roznoženie", "Roznožení"),
    ("Full", "Plný", "Plný"),
]

# ladder name -> (sk, cs, [(exercise, (label, sk, cs), goal_sets, goal_value)])
LADDERS = {
    "Front Lever": ("Front lever", "Front lever", [
        ("Tuck Front Lever", LEVER_RUNGS[0], 3, 15),
        ("Advanced Tuck Front Lever", LEVER_RUNGS[1], 3, 12),
        ("One Leg Front Lever", LEVER_RUNGS[2], 3, 10),
        ("Straddle Front Lever", LEVER_RUNGS[3], 3, 8),
        ("Front Lever", LEVER_RUNGS[4], 3, 6),
    ]),
    "Front Lever Negative": ("Spúšťanie do front leveru", "Spouštění do front leveru", [
        ("Tuck Front Lever Negative", LEVER_RUNGS[0], 3, 8),
        ("Advanced Tuck Front Lever Negative", LEVER_RUNGS[1], 3, 6),
        ("One Leg Front Lever Negative", LEVER_RUNGS[2], 3, 5),
        ("Straddle Front Lever Negative", LEVER_RUNGS[3], 3, 4),
        ("Front Lever Negative", LEVER_RUNGS[4], 3, 3),
    ]),
}


def missing_tables(conn):
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return [t for t in TABLES if t not in have]


def plan(conn, tables_missing):
    """[(ladder, sk, cs, [(exercise_id, level, label, sk, cs, sets, value)])] still to add."""
    todo = []
    for name, (sk, cs, levels) in LADDERS.items():
        if not tables_missing and conn.execute(
                "SELECT 1 FROM progressions WHERE name = ?", (name,)).fetchone():
            print(f"  ladder already there: {name}")
            continue
        rows = []
        for level, (exercise, (label, label_sk, label_cs), goal_sets, goal_value) in enumerate(levels, 1):
            row = conn.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?",
                               (exercise,)).fetchone()
            if row is None:
                print(f"  {name}: no exercise '{exercise}' - level {level} skipped")
                continue
            if not tables_missing and conn.execute(
                    "SELECT 1 FROM progression_levels WHERE exercise_id = ?", (row[0],)).fetchone():
                print(f"  {name}: '{exercise}' is already a level of another ladder - skipped")
                continue
            rows.append((row[0], level, label, label_sk, label_cs, goal_sets, goal_value))
        todo.append((name, sk, cs, rows))
    return todo


def main():
    apply = "--apply" in sys.argv[1:]
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        tables_missing = missing_tables(conn)
        for t in tables_missing:
            print(f"  create table {t}")
        todo = plan(conn, tables_missing)
        for name, _, _, rows in todo:
            print(f"  add ladder {name}: " + ", ".join(f"{r[1]}. {r[2]}" for r in rows))

        if not tables_missing and not todo:
            print("Nothing to do.")
            return
        if not apply:
            print("\nDry run. Run with --apply to do it.")
            return

        backup = f"{DB_PATH}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        conn.close()
        shutil.copy2(DB_PATH, backup)
        print(f"\nBackup: {backup}")

        conn = sqlite3.connect(DB_PATH)
        with conn:
            for t in tables_missing:
                conn.execute(TABLES[t])
            for sql in INDEXES:
                conn.execute(sql)
            for name, sk, cs, rows in todo:
                pid = conn.execute("INSERT INTO progressions (name, name_sk, name_cs) VALUES (?, ?, ?)",
                                   (name, sk, cs)).lastrowid
                conn.executemany(
                    "INSERT INTO progression_levels (progression_id, exercise_id, level, label, "
                    "label_sk, label_cs, goal_sets, goal_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(pid, *r) for r in rows])
        print(f"Created {len(tables_missing)} tables, added {len(todo)} ladders.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
