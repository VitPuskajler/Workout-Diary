"""One-off migration: let an exercise be measured in seconds instead of reps.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

Adds exercises.is_timed (0/1, default 0) and flags the hold exercises: planks,
levers, handstands, wall squats, hangs, bridges and every yoga "... Pose".
The sets themselves are untouched - the seconds live in the existing reps
column, only the labels change.

Safe to run twice; it checks before it changes anything. More exercises can be
flagged afterwards from the "Reps / Sec" button on /create_workout.

    python temp/add_timed_column.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

HOLD_EXERCISES = [
    "Tuck Front Lever",
    "Advanced Tuck Front Lever",
    "Straddle Front Lever",
    "Front Lever",
    "Back-to-Wall Handstand",
    "Chest-to-Wall Handstand",
    "Plank",
    "Side Plank",
    "Bench Plank",
    "Stability Ball Plank",
    "Stability Ball Full Body Plank",
    "Bodyweight Wall Squat",
    "Dumbbell Wall Squat",
    "Stability Ball Wall Squat",
    "Stability Ball Weighted Wall Squat",
    "One-Arm Hang",
    "One-Arm Pull-Up Hold",
    "Side Bridge",
    "Isometric Chest Press",
    "Bridge",
]


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(exercises)")]

        if "is_timed" in columns:
            print("is_timed column already present - nothing to add")
        else:
            conn.execute(
                "ALTER TABLE exercises ADD COLUMN is_timed BOOLEAN "
                "NOT NULL DEFAULT 0"
            )
            print("is_timed column added, every exercise defaulted to reps")

        flagged = 0
        for name in HOLD_EXERCISES:
            cursor = conn.execute(
                "UPDATE exercises SET is_timed = 1 WHERE exercise_name = ?", (name,)
            )
            if cursor.rowcount == 0:
                print(f"  not found in this database: {name}")
            flagged += cursor.rowcount

        poses = conn.execute(
            "UPDATE exercises SET is_timed = 1 WHERE exercise_name LIKE '% Pose%'"
        ).rowcount
        conn.commit()

        print(f"\nflagged {flagged} named holds, {poses} yoga poses (already-flagged ones included)")
        print("\ncurrently timed:")
        for (name,) in conn.execute(
            "SELECT exercise_name FROM exercises WHERE is_timed = 1 ORDER BY exercise_name"
        ):
            print(f"  {name}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
