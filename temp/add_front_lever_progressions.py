"""One-off data change: the front lever ladder.

  - registers the rungs the catalog was missing (NEW_EXERCISES): the one leg
    hold, and a negative for every rung - from the top (pulled up, thighs on
    the bar) lowered slowly into the lever
  - moves the holds that borrowed the Front Lever Raise drawing onto their own
    (OWN_DRAWINGS) - only while they still have it, so a pick made on
    /admin/exercises since is left alone

The drawings come from tools/make_exercise_icons.py (LEVER_HOLDS,
LEVER_NEGATIVES); the files must be in static/icons/exercises first, which
they are after a pull. A new exercise gets no icon value: it uses the drawing
named after it.

Safe to run twice: an exercise already in the catalog (by name, any case) is
skipped. Plain sqlite3, like the other scripts here. Without --apply it only
prints what it would do. With --apply it first copies the database to
instance/workout.db.bak-<timestamp>, then makes the changes in one
transaction.

    python temp/add_front_lever_progressions.py            # dry run
    python temp/add_front_lever_progressions.py --apply    # make the changes
"""
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "instance", "workout.db")
ICON_DIR = os.path.join(ROOT, "static", "icons", "exercises")

# (name, muscle_group, is_timed, name_sk, name_cs)
NEW_EXERCISES = [
    ("One Leg Front Lever", "back", 1,
     "Front lever s jednou nohou", "Front lever s jednou nohou"),
    ("Tuck Front Lever Negative", "back", 0,
     "Spúšťanie do front leveru v skrčení", "Spouštění do front leveru ve skrčení"),
    ("Advanced Tuck Front Lever Negative", "back", 0,
     "Spúšťanie do front leveru v pokročilom skrčení", "Spouštění do front leveru v pokročilém skrčení"),
    ("One Leg Front Lever Negative", "back", 0,
     "Spúšťanie do front leveru s jednou nohou", "Spouštění do front leveru s jednou nohou"),
    ("Straddle Front Lever Negative", "back", 0,
     "Spúšťanie do front leveru v roznožení", "Spouštění do front leveru v roznožení"),
    ("Front Lever Negative", "back", 0,
     "Spúšťanie do front leveru", "Spouštění do front leveru"),
]

# exercise -> the drawing it borrowed until now
OWN_DRAWINGS = {
    "Advanced Tuck Front Lever": "front-lever-raise",
    "Straddle Front Lever": "front-lever-raise",
    "Front Lever": "front-lever-raise",
}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def has_drawing(name):
    return os.path.exists(os.path.join(ICON_DIR, slug(name) + ".svg"))


def plan(conn, new_exercises, own_drawings):
    """(inserts, icon moves) still to do."""
    inserts = []
    for row in new_exercises:
        name = row[0]
        if conn.execute("SELECT 1 FROM exercises WHERE lower(exercise_name) = lower(?)",
                        (name,)).fetchone():
            print(f"  already in the catalog: {name}")
            continue
        if not has_drawing(name):
            print(f"  note: no drawing {slug(name)}.svg yet - run tools/make_exercise_icons.py")
        inserts.append(row)

    moves = []
    for name, old_icon in own_drawings.items():
        row = conn.execute("SELECT icon FROM exercises WHERE exercise_name = ?", (name,)).fetchone()
        if row is None:
            print(f"  not in the catalog: {name} - skipped")
        elif not has_drawing(name):
            print(f"  no drawing {slug(name)}.svg yet - {name} keeps {row[0]}")
        elif row[0] == slug(name):
            print(f"  already on its own drawing: {name}")
        elif row[0] != old_icon:
            print(f"  {name} has icon {row[0]} picked by hand - left alone")
        else:
            moves.append((name, old_icon))
    return inserts, moves


def run(new_exercises, own_drawings):
    """The dry run / --apply for one list - temp/add_handstand_progressions.py
    uses it too."""
    apply = "--apply" in sys.argv[1:]
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        inserts, moves = plan(conn, new_exercises, own_drawings)
        for name, group, timed, sk, cs in inserts:
            kind = "hold, timed" if timed else "reps"
            print(f"  add {name} ({group}, {kind}) - SK: {sk} / CS: {cs}")
        for name, old_icon in moves:
            print(f"  icon {name}: {old_icon} -> {slug(name)}")

        if not inserts and not moves:
            print("Nothing to do.")
            return
        if not apply:
            print(f"\nDry run: {len(inserts)} exercises to add, {len(moves)} icons to move. "
                  "Run with --apply to do it.")
            return

        backup = f"{DB_PATH}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        conn.close()
        shutil.copy2(DB_PATH, backup)
        print(f"\nBackup: {backup}")

        conn = sqlite3.connect(DB_PATH)
        with conn:
            conn.executemany(
                "INSERT INTO exercises (exercise_name, muscle_group, is_timed, is_deleted, name_sk, name_cs) "
                "VALUES (?, ?, ?, 0, ?, ?)", inserts)
            for name, old_icon in moves:
                conn.execute("UPDATE exercises SET icon = ? WHERE exercise_name = ? AND icon = ?",
                             (slug(name), name, old_icon))
        print(f"Added {len(inserts)} exercises, moved {len(moves)} icons.")
    finally:
        conn.close()


if __name__ == "__main__":
    run(NEW_EXERCISES, OWN_DRAWINGS)
