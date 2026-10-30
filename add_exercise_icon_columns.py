"""One-off migration: exercise icons and soft delete for /admin/exercises.

db.create_all() only creates tables that do not exist - it will never add a
column to a table that already does. So this has to be done by hand, once per
database: locally, and again on PythonAnywhere.

  - exercises.icon (text, NULL)       which drawing in static/icons/exercises an
                                      exercise uses; NULL = the one named after it
  - exercises.is_deleted (0/1, 0)     "deleted" exercises stay in the table so
                                      their logged sets keep a name, but no
                                      picker offers them any more
  - registers exercises the catalog was missing (NEW_EXERCISES)
  - points variants at a shared drawing (ICON_ALIASES), then every other
    exercise at the icon make_exercise_icons.py generated for it
    (data/exercise_icons.json) - only where the exercise has no icon chosen
    yet, so a pick made on /admin/exercises wins

Safe to run twice; it checks before it changes anything.

    python add_exercise_icon_columns.py
"""
import json
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "instance", "workout.db")

# (name, muscle_group, is_timed)
NEW_EXERCISES = [
    ("Decline Push-Up (Handles)", "chest", 0),
]

# exercise name -> icon file name (without .svg)
ICON_ALIASES = {
    "Barbell Romanian Deadlift": "barbell-stiff-leg-deadlift",
    "Dumbbell Stiff-Leg Deadlift": "barbell-stiff-leg-deadlift",
    "Machine Squat": "hack-squat",
    "Hack Squat (Narrow Stance)": "hack-squat",
    "Barbell Squat with Narrow Stance": "barbell-squat",
    "EZ Bar Close Grip Curl": "ez-bar-curl",
    "Cable Lat Pulldown (Wide Grip)": "machine-lat-pulldown",
    "Cable Front Lat Pulldown (Close Grip)": "machine-lat-pulldown",
    "Cable Grip Lat Pulldown (Narrow Grip)": "machine-lat-pulldown",
    "Machine One-Arm Pulldown": "machine-lat-pulldown",
    "Machine Leg Press (Narrow Stance)": "machine-leg-press",
    "Machine Shoulder Press": "dumbbell-shoulder-press",
    "Smith Machine Shoulder Press": "barbell-military-press",
    "Cable Tricep Pushdown (V-Bar)": "cable-tricep-extension",
    "Cable Tricep Pushdown (Rope)": "cable-tricep-extension",
    "Machine Incline Chest Press": "dumbbell-incline-bench-press",
    "Barbell Incline Bench Press": "dumbbell-incline-bench-press",
    "Machine Bench Press": "barbell-bench-press",
    "Dumbbell Bench Press (Palms in)": "dumbbell-bench-press",
    "Dumbbell Seated Side Lateral Raise": "dumbbell-lateral-raise",
    "Cable Side Lateral Raise": "dumbbell-lateral-raise",
    "Machine Seated Tricep Dip": "dip",
    "Machine Dip": "dip",
    "Weighted Tricep Dip": "dip",
    "Machine Ab Crunch": "bench-crunch",
    "Dumbbell Hammer Curl": "dumbbell-bicep-curl",
    "Dumbbell Seated Bicep Curl": "dumbbell-bicep-curl",
    "Cable Bicep Curl": "dumbbell-bicep-curl",
    "Dumbbell Prone Deltoid Raise": "machine-reverse-fly",
    "Band Assisted Muscle-Up": "muscle-up",
    "Elevated Push-Up": "bench-push-up",
    "Cable One-Arm Seated Row": "cable-seated-row",
    "Assisted One-Arm Pull-Up": "pull-up",
    "Chin-Up": "pull-up",
    "EZ Bar Tricep Extension (Close Grip)": "ez-bar-tricep-extension",
    "Barbell JM Press": "ez-bar-tricep-extension",
    "Smith Machine Bulgarian Split Squat": "barbell-bulgarian-split-squat",
}


def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(exercises)")]

        if "icon" in columns:
            print("icon column already present - nothing to add")
        else:
            conn.execute("ALTER TABLE exercises ADD COLUMN icon VARCHAR(100)")
            print("icon column added")

        if "is_deleted" in columns:
            print("is_deleted column already present - nothing to add")
        else:
            conn.execute(
                "ALTER TABLE exercises ADD COLUMN is_deleted BOOLEAN "
                "NOT NULL DEFAULT 0"
            )
            print("is_deleted column added, no exercise deleted")

        for name, group, timed in NEW_EXERCISES:
            exists = conn.execute(
                "SELECT 1 FROM exercises WHERE lower(exercise_name) = lower(?)", (name,)
            ).fetchone()
            if exists:
                print(f"  already in the catalog: {name}")
            else:
                conn.execute(
                    "INSERT INTO exercises (exercise_name, muscle_group, is_timed) "
                    "VALUES (?, ?, ?)", (name, group, timed)
                )
                print(f"  registered: {name} ({group})")

        icon_dir = os.path.join(os.path.dirname(DB_PATH), "..", "static", "icons", "exercises")
        linked = 0
        for name, icon in ICON_ALIASES.items():
            if not os.path.exists(os.path.join(icon_dir, icon + ".svg")):
                print(f"  no drawing {icon}.svg - skipped {name}")
                continue
            linked += conn.execute(
                "UPDATE exercises SET icon = ? WHERE exercise_name = ? AND icon IS NULL",
                (icon, name),
            ).rowcount
        conn.commit()
        print(f"\npointed {linked} exercises at a shared drawing")

        # Everything else gets the icon make_exercise_icons.py built for it.
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "exercise_icons.json")
        if os.path.exists(map_path):
            with open(map_path, encoding="utf-8") as handle:
                generated = json.load(handle)
            matched = 0
            for name, icon in generated.items():
                if not os.path.exists(os.path.join(icon_dir, icon + ".svg")):
                    continue
                matched += conn.execute(
                    "UPDATE exercises SET icon = ? WHERE exercise_name = ? AND icon IS NULL",
                    (icon, name),
                ).rowcount
            conn.commit()
            print(f"gave {matched} more exercises their generated icon")
        else:
            print("no data/exercise_icons.json - run make_exercise_icons.py first")

        missing = conn.execute(
            "SELECT count(*) FROM exercises WHERE icon IS NULL"
        ).fetchone()[0]
        print(f"{missing} exercises have no icon set (they may still have one named after them)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
