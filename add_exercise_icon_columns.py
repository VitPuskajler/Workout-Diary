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
  - clears icons whose drawing no longer exists
  - moves exercises onto a drawing of their own once they have one
    (OWN_DRAWINGS)
  - points variants at a shared drawing (ICON_ALIASES), then every other
    exercise at the icon make_exercise_icons.py generated for it
    (data/exercise_icons.json) - only where the exercise has no icon chosen
    yet, so a pick made on /admin/exercises wins

Safe to run twice; it checks before it changes anything.

    python add_exercise_icon_columns.py
"""
import json
import os
import re
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
    "Band Assisted Muscle-Up": "muscle-up",
}

# Exercises that shared a sibling's drawing and now have their own (the third
# batch in make_exercise_icons.py): exercise -> the drawing it used to share.
# Moved only while it still has that one - a pick made on /admin/exercises
# since is left alone.
OWN_DRAWINGS = {
    "Cable Lat Pulldown (Wide Grip)": "machine-lat-pulldown",
    "Cable Front Lat Pulldown (Close Grip)": "machine-lat-pulldown",
    "Cable Grip Lat Pulldown (Narrow Grip)": "machine-lat-pulldown",
    "Machine One-Arm Pulldown": "machine-lat-pulldown",
    "Cable Bicep Curl": "dumbbell-bicep-curl",
    "Dumbbell Hammer Curl": "dumbbell-bicep-curl",
    "Dumbbell Seated Bicep Curl": "dumbbell-bicep-curl",
    "Machine Dip": "dip",
    "Machine Seated Tricep Dip": "dip",
    "Weighted Tricep Dip": "dip",
    "Barbell Incline Bench Press": "dumbbell-incline-bench-press",
    "Machine Incline Chest Press": "dumbbell-incline-bench-press",
    "Cable Side Lateral Raise": "dumbbell-lateral-raise",
    "Dumbbell Seated Side Lateral Raise": "dumbbell-lateral-raise",
    "Chin-Up": "pull-up",
    "Assisted One-Arm Pull-Up": "pull-up",
    "Cable Tricep Pushdown (Rope)": "cable-tricep-extension",
    "Cable Tricep Pushdown (V-Bar)": "cable-tricep-extension",
    "Barbell Romanian Deadlift": "barbell-stiff-leg-deadlift",
    "Dumbbell Stiff-Leg Deadlift": "barbell-stiff-leg-deadlift",
    "Machine Ab Crunch": "bench-crunch",
    "Oblique Crunch": "bench-crunch",
    "EZ Bar Tricep Extension (Close Grip)": "ez-bar-tricep-extension",
    "Barbell JM Press": "ez-bar-tricep-extension",
    "Hack Squat (Narrow Stance)": "hack-squat",
    "Machine Squat": "hack-squat",
    "Machine Leg Press (Narrow Stance)": "machine-leg-press",
    "Machine Single-Leg Press": "machine-leg-press",
    "Machine Shoulder Press": "dumbbell-shoulder-press",
    "Barbell Squat with Narrow Stance": "barbell-squat",
    "Smith Machine Shoulder Press": "barbell-military-press",
    "EZ Bar Close Grip Curl": "ez-bar-curl",
    "Dumbbell Bench Press (Palms in)": "dumbbell-bench-press",
    "Cable One-Arm Seated Row": "cable-seated-row",
    "Machine Bench Press": "barbell-bench-press",
    "Dumbbell Prone Deltoid Raise": "machine-reverse-fly",
    "Smith Machine Bulgarian Split Squat": "barbell-bulgarian-split-squat",
    "Elevated Push-Up": "bench-push-up",
}


# Generated icons the fourth batch in make_exercise_icons.py split into one
# drawing per movement (core, leg raises, yoga / stretches, Olympic lifts,
# rear delts). An exercise still on one of these is moved to the icon the
# generator gives it now; a pick made on /admin/exercises since is left alone
# unless it is one of these.
REGROUPED = {
    "bench-crunch", "leg-raise", "x-stretch-side-none", "x-stretch-fold-none",
    "x-overhead-lift-barbell", "x-rear-raise-dumbbell",
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

        # An icon whose drawing make_exercise_icons.py no longer makes (the
        # exercise was moved to a better one) is not a pick worth keeping -
        # cleared, so the steps below give it its current drawing.
        drawings = {f[:-4] for f in os.listdir(icon_dir) if f.endswith(".svg")}
        stale = [(name, icon) for name, icon in conn.execute(
            "SELECT exercise_name, icon FROM exercises WHERE icon IS NOT NULL") if icon not in drawings]
        conn.executemany("UPDATE exercises SET icon = NULL WHERE exercise_name = ?",
                         [(name,) for name, _ in stale])
        for name, icon in stale:
            print(f"  {name}: drawing {icon}.svg is gone - icon cleared")

        own = 0
        for name, old_icon in OWN_DRAWINGS.items():
            icon = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if icon not in drawings:
                print(f"  no drawing {icon}.svg yet - {name} keeps {old_icon}")
                continue
            own += conn.execute(
                "UPDATE exercises SET icon = ? WHERE exercise_name = ? AND icon = ?",
                (icon, name, old_icon),
            ).rowcount
        print(f"moved {own} exercises onto a drawing of their own")

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

            regrouped = 0
            for name, icon in generated.items():
                if not os.path.exists(os.path.join(icon_dir, icon + ".svg")):
                    continue
                regrouped += conn.execute(
                    "UPDATE exercises SET icon = ? WHERE exercise_name = ? AND icon != ? AND icon IN (%s)"
                    % ",".join("?" * len(REGROUPED)),
                    (icon, name, icon, *sorted(REGROUPED)),
                ).rowcount
            conn.commit()
            print(f"moved {regrouped} exercises from a shared drawing onto their movement's own")
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
