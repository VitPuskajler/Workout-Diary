"""One-off data fix: move Vito's explosive pull-up sets from Pull-Up to
Explosive Pull-Up.

Since 2026-09-16 the pull-up workout has been 4 sets: the first two are
weighted strength sets (3-5 reps), the last two are explosive bodyweight
sets. Until 2026-11-03 the explosive sets were logged under Pull-Up because
the Explosive Pull-Up exercise did not exist yet. This moves those 10 sets:

    session 302 (2026-09-16)  entries 2701, 2702
    session 305 (2026-09-24)  entries 2747, 2748  (logged with 0 reps -> 3)
    session 307 (2026-10-01)  entries 2774, 2775
    session 311 (2026-10-10)  entries 2799, 2800
    session 319 (2026-10-29)  entries 2851, 2852

Within each session the moved sets are renumbered from 1, because they are
now their own exercise (that is how session 323 logs them).

Each entry is changed only if it still looks the way it did when this list
was made: same session, exercise Pull-Up, bodyweight. Any other entry is
reported and left alone. An entry already on Explosive Pull-Up is skipped,
so running this twice does nothing the second time.

Plain sqlite3, like the other scripts here. Without --apply it only prints
what it would do. With --apply it first copies the database to
instance/workout.db.bak-<timestamp>, then makes the changes in one
transaction.

    python temp/move_explosive_pull_ups.py            # dry run
    python temp/move_explosive_pull_ups.py --apply    # make the changes
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

PULL_UP = "Pull-Up"
EXPLOSIVE = "Explosive Pull-Up"
EXPLOSIVE_REPS = 3  # used when the set was logged with 0 reps

# session_id -> entry_ids, in their original set order
MOVES = {
    302: [2701, 2702],
    305: [2747, 2748],
    307: [2774, 2775],
    311: [2799, 2800],
    319: [2851, 2852],
}


def exercise_id(conn, name):
    row = conn.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?",
                       (name,)).fetchone()
    if row is None:
        sys.exit(f"Exercise '{name}' not found in the database.")
    return row[0]


def plan(conn, pull_up_id, explosive_id):
    """Return [(entry_id, session_id, old_set, new_set, old_reps, new_reps)]."""
    changes = []
    for session_id, entry_ids in MOVES.items():
        new_set = 1
        for entry_id in entry_ids:
            row = conn.execute(
                "SELECT session_id, exercise_id, set_number, reps, weight "
                "FROM exercise_entries WHERE entry_id = ?", (entry_id,)).fetchone()
            if row is None:
                print(f"  entry {entry_id}: not found - skipped")
                continue
            sid, ex_id, set_number, reps, weight = row
            if ex_id == explosive_id:
                print(f"  entry {entry_id}: already Explosive Pull-Up - skipped")
                continue
            if sid != session_id or ex_id != pull_up_id or (weight or 0) != 0:
                print(f"  entry {entry_id}: does not match (session {sid}, exercise "
                      f"{ex_id}, weight {weight}) - skipped")
                continue
            new_reps = reps if reps else EXPLOSIVE_REPS
            changes.append((entry_id, session_id, set_number, new_set, reps, new_reps))
            new_set += 1
    return changes


def main():
    apply = "--apply" in sys.argv[1:]
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        pull_up_id = exercise_id(conn, PULL_UP)
        explosive_id = exercise_id(conn, EXPLOSIVE)
        changes = plan(conn, pull_up_id, explosive_id)

        if not changes:
            print("Nothing to move.")
            return
        for entry_id, session_id, old_set, new_set, old_reps, new_reps in changes:
            reps = f"reps {old_reps}" if old_reps == new_reps else f"reps {old_reps} -> {new_reps}"
            print(f"  entry {entry_id} (session {session_id}): Pull-Up set {old_set} "
                  f"-> Explosive Pull-Up set {new_set}, {reps}")

        if not apply:
            print(f"\nDry run: {len(changes)} sets would move. Run with --apply to do it.")
            return

        backup = f"{DB_PATH}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        conn.close()
        shutil.copy2(DB_PATH, backup)
        print(f"\nBackup: {backup}")

        conn = sqlite3.connect(DB_PATH)
        with conn:
            for entry_id, _, _, new_set, _, new_reps in changes:
                conn.execute(
                    "UPDATE exercise_entries SET exercise_id = ?, set_number = ?, reps = ? "
                    "WHERE entry_id = ?", (explosive_id, new_set, new_reps, entry_id))
        print(f"Moved {len(changes)} sets to Explosive Pull-Up.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
