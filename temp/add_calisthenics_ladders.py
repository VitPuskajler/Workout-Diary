"""One-off data change: calisthenics ladders, merged near-duplicates, bands.

Rule: a LEVEL changes the exercise, a LOAD changes a number on the set.
Bands are load, so they are a number (kg) on the set, never an exercise.

  1. columns
     - exercise_entries.band_kg  band resistance in kg on that set (NULL = no
       band; two bands = their sum)
     - exercises.band_mode       what a band does on this exercise: 'assist'
       (helps: pull-up work, muscle-up), 'resist' (makes it harder:
       push-ups) or NULL (bands not used)
  2. new exercises the ladders need (NEW_EXERCISES); Elevated Push-Up is
     renamed to Decline Push-Up (feet on a bench - that is what it always was)
  3. sets moved off exercises that were only a variation of another one
     (MOVES); band colours in the notes become band_kg (BAND_KG_BY_ENTRY)
  4. those exercises are hidden (is_deleted = 1, HIDE) and plan rows that
     pointed at them point at the new exercise
  5. the ladders (LADDERS) and band_mode (BAND_MODE)

Leg Raise stays visible (another user has it in a plan); only Vito's six
hanging sets move to Hanging Leg Raise. Bench Push-Up stays as the easiest
push-up level (hands on a bench); Vito's two sets on it were decline with
handles, so they move.

Run temp/move_explosive_pull_ups.py too - it is the same clean-up for
explosive pull-ups.

Safe to run twice: every step checks whether it is still needed. Plain
sqlite3, like the other scripts here. Without --apply it only prints what it
would do. With --apply it first copies the database to
instance/workout.db.bak-<timestamp>, then makes the changes in one
transaction.

    python temp/add_calisthenics_ladders.py            # dry run
    python temp/add_calisthenics_ladders.py --apply    # make the changes
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "instance", "workout.db")

# Band colour -> kg: the middle of the range printed on the band
# (yellow 2-7, red 7-16, black 11-30, purple 16-39, green 23-57).
YELLOW, RED, BLACK, PURPLE, GREEN = 4.5, 11.5, 20.5, 27.5, 40.0

COLUMNS = [
    ("exercise_entries", "band_kg", "ALTER TABLE exercise_entries ADD COLUMN band_kg FLOAT"),
    ("exercises", "band_mode", "ALTER TABLE exercises ADD COLUMN band_mode VARCHAR(10)"),
]

# (name, muscle_group, is_timed, name_sk, name_cs, icon)
NEW_EXERCISES = [
    ("Archer Pull-Up", "back", 0, "Lukostrelecký zhyb", "Lukostřelecký shyb", "pull-up"),
    ("Parallel Bar Knee Raise", "abs", 0,
     "Zdvíhanie kolien na bradlách", "Zvedání kolen na bradlech", "parallel-bar-leg-raise"),
    ("Standing Ab Roll", "abs", 0,
     "Posilňovacie koliesko v stoji", "Posilovací kolečko ve stoje", "ab-roll"),
]

# old name -> (new name, sk, cs). The icon is already pinned by file name.
RENAMES = {
    "Elevated Push-Up": ("Decline Push-Up", "Kľuky s nohami vyššie", "Kliky s nohama výš"),
}

# Names fixed once the duplicate One Arm Pull-Up is hidden.
TRANSLATION_FIXES = {
    "One-Arm Pull-Up": ("Zhyb jednou rukou", "Shyb jednou rukou"),
}

# (from exercise, to exercise, only this user's sets or None for everyone)
MOVES = [
    ("Bench Push-Up", "Decline Push-Up (handles)", "Vito"),
    ("Weighted Tricep Dip", "Dip", None),
    ("Leg Raise", "Hanging Leg Raise", "Vito"),
    ("Front Lever Raise", "Tuck Front Lever Negative", None),
    ("Band Assisted Muscle-Up", "Strict Muscle-Up", None),
    ("Assisted One-Arm Pull-Up", "One-Arm Pull-Up", None),
]

# entry_id -> (band_kg, weight). The band colour was only in the notes; in
# June 2025 the weight box held a guess of the band's help (-20 / +-15), now
# it goes back to 0 (no vest, no plates).
BAND_KG_BY_ENTRY = {
    # Band Assisted Muscle-Up
    698: (PURPLE, 0.0), 699: (BLACK, 0.0), 700: (BLACK, 0.0), 741: (BLACK, 0.0),
    791: (BLACK, 0.0), 1758: (2 * GREEN, 0.0), 1759: (PURPLE, 0.0), 1760: (BLACK, 0.0),
    1837: (PURPLE, 0.0), 1838: (BLACK, 0.0),
    # Assisted One-Arm Pull-Up - always the purple band
    678: (PURPLE, 0.0), 679: (PURPLE, 0.0), 720: (PURPLE, 0.0), 721: (PURPLE, 0.0),
    754: (PURPLE, 0.0), 755: (PURPLE, 0.0), 796: (PURPLE, 0.0),
}

# exercise hidden -> the exercise its plan rows now use
HIDE = {
    "Weighted Tricep Dip": "Dip",
    "Front Lever Raise": "Tuck Front Lever Negative",
    "Band Assisted Muscle-Up": "Strict Muscle-Up",
    "Assisted One-Arm Pull-Up": "One-Arm Pull-Up",
    "One Arm Pull-Up": "One-Arm Pull-Up",
}

BAND_MODE = {
    "assist": ["Explosive Pull-Up", "Archer Pull-Up", "Negative One-Arm Pull-Up",
               "One-Arm Pull-Up", "Strict Muscle-Up", "Slow Muscle-Up", "Kipping Muscle-Up"],
    "resist": ["Bench Push-Up", "Push-Up", "Decline Push-Up", "Decline Push-Up (handles)"],
}

# ladder -> (sk, cs, [(exercise, (label, sk, cs), goal_sets, goal_value)])
LADDERS = {
    "Push-Up": ("Kľuky", "Kliky", [
        ("Bench Push-Up", ("Hands on bench", "Ruky na lavičke", "Ruce na lavičce"), 3, 20),
        ("Push-Up", ("Floor", "Na zemi", "Na zemi"), 3, 20),
        ("Decline Push-Up", ("Feet on bench", "Nohy na lavičke", "Nohy na lavičce"), 3, 15),
        ("Decline Push-Up (handles)", ("Feet on bench + handles", "Nohy na lavičke + rúčky",
                                       "Nohy na lavičce + madla"), 3, 15),
    ]),
    "One-Arm Pull-Up": ("Zhyb jednou rukou", "Shyb jednou rukou", [
        ("Archer Pull-Up", ("Archer", "Lukostrelec", "Lukostřelec"), 3, 8),
        ("Negative One-Arm Pull-Up", ("Negative", "Negatív", "Negativ"), 3, 5),
        ("One-Arm Pull-Up", ("Full", "Plný", "Plný"), 3, 3),
    ]),
    "Muscle-Up": ("Muscle-up", "Muscle-up", [
        ("Strict Muscle-Up", ("Strict", "Striktný", "Striktní"), 3, 3),
        ("Slow Muscle-Up", ("Slow", "Pomalý", "Pomalý"), 3, 3),
    ]),
    "Parallel Bar Leg Raise": ("Zdvihy nôh na bradlách", "Zvedání nohou na bradlech", [
        ("Parallel Bar Knee Raise", ("Bent knees", "Skrčené nohy", "Pokrčené nohy"), 3, 15),
        ("Parallel Bar Leg Raise", ("Straight legs", "Vystreté nohy", "Natažené nohy"), 3, 15),
    ]),
    "Ab Roll": ("Posilňovacie koliesko", "Posilovací kolečko", [
        ("Ab Roll", ("Kneeling", "Z kolien", "Z kolen"), 3, 10),
        ("Standing Ab Roll", ("Standing", "V stoji", "Ve stoje"), 3, 5),
    ]),
}


class Plan:
    def __init__(self):
        self.columns, self.inserts, self.renames, self.names = [], [], [], []
        self.moves, self.bands, self.hides, self.plan_rows = [], [], [], []
        self.modes, self.ladders = [], []

    def empty(self):
        return not any(vars(self).values())


def exercise_id(conn, name):
    row = conn.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (name,)).fetchone()
    return row[0] if row else None


def has_column(conn, table, column):
    return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))


def make_plan(conn):
    p = Plan()
    for table, column, sql in COLUMNS:
        if not has_column(conn, table, column):
            p.columns.append(sql)

    # Names as they will be once the renames and inserts are done.
    future = {}
    for old, (new, sk, cs) in RENAMES.items():
        old_id, new_id = exercise_id(conn, old), exercise_id(conn, new)
        if new_id:
            future[new] = new_id
        elif old_id:
            p.renames.append((old_id, old, new, sk, cs))
            future[new] = old_id
        else:
            print(f"  rename: neither '{old}' nor '{new}' in the catalog")
    for row in NEW_EXERCISES:
        if conn.execute("SELECT 1 FROM exercises WHERE lower(exercise_name) = lower(?)",
                        (row[0],)).fetchone():
            print(f"  already in the catalog: {row[0]}")
        else:
            p.inserts.append(row)

    def resolve(name):
        return future.get(name) or exercise_id(conn, name)

    for name, (sk, cs) in TRANSLATION_FIXES.items():
        if conn.execute("SELECT 1 FROM exercises WHERE exercise_name = ? AND "
                        "(name_sk IS NOT ? OR name_cs IS NOT ?)", (name, sk, cs)).fetchone():
            p.names.append((name, sk, cs))

    for src, dst, only_user in MOVES:
        src_id, dst_id = exercise_id(conn, src), resolve(dst)
        if src_id is None or dst_id is None:
            print(f"  move {src} -> {dst}: exercise missing - skipped")
            continue
        sql = ("SELECT e.entry_id, e.session_id FROM exercise_entries e "
               "JOIN sessions s ON s.session_id = e.session_id "
               "JOIN users u ON u.user_id = s.user_id WHERE e.exercise_id = ?")
        args = [src_id]
        if only_user:
            sql += " AND u.username = ?"
            args.append(only_user)
        rows = conn.execute(sql + " ORDER BY e.session_id, e.set_number, e.entry_id", args).fetchall()
        if rows:
            p.moves.append((src, dst, dst_id, rows))

    for entry_id, (band, weight) in BAND_KG_BY_ENTRY.items():
        row = conn.execute("SELECT 1 FROM exercise_entries WHERE entry_id = ?", (entry_id,)).fetchone()
        if row is None:
            print(f"  band: no entry {entry_id} - skipped")
            continue
        if p.columns or conn.execute("SELECT 1 FROM exercise_entries WHERE entry_id = ? "
                                     "AND band_kg IS NOT ?", (entry_id, band)).fetchone():
            p.bands.append((entry_id, band, weight))

    for name, target in HIDE.items():
        ex_id, target_id = exercise_id(conn, name), resolve(target)
        if ex_id is None:
            print(f"  hide: no exercise '{name}' - skipped")
            continue
        if conn.execute("SELECT is_deleted FROM exercises WHERE exercise_id = ?", (ex_id,)).fetchone()[0] == 0:
            p.hides.append((ex_id, name))
        for (we_id, workout) in conn.execute(
                "SELECT we.workout_exercise_id, w.workout_name || ' #' || w.workout_id "
                "FROM workout_exercises we JOIN workouts w ON w.workout_id = we.workout_id "
                "WHERE we.exercise_id = ?", (ex_id,)):
            p.plan_rows.append((we_id, workout, name, target, target_id))

    for mode, names in BAND_MODE.items():
        for name in names:
            ex_id = resolve(name)
            if ex_id is None and name in [r[0] for r in p.inserts]:
                p.modes.append((name, name, mode))      # inserted in the same transaction
            elif ex_id is None:
                print(f"  band_mode: no exercise '{name}' - skipped")
            elif p.columns or conn.execute("SELECT 1 FROM exercises WHERE exercise_id = ? "
                                           "AND band_mode IS NOT ?", (ex_id, mode)).fetchone():
                p.modes.append((name, ex_id, mode))

    for ladder, (sk, cs, levels) in LADDERS.items():
        if conn.execute("SELECT 1 FROM progressions WHERE name = ?", (ladder,)).fetchone():
            print(f"  ladder already there: {ladder}")
            continue
        rows = []
        for level, (name, (label, lsk, lcs), goal_sets, goal_value) in enumerate(levels, 1):
            ex_id = resolve(name)
            if ex_id is None and name in [r[0] for r in p.inserts]:
                ex_id = name            # inserted in the same transaction
            if ex_id is None:
                print(f"  {ladder}: no exercise '{name}' - level skipped")
                continue
            if isinstance(ex_id, int) and conn.execute(
                    "SELECT 1 FROM progression_levels WHERE exercise_id = ?", (ex_id,)).fetchone():
                print(f"  {ladder}: '{name}' is already a level of another ladder - skipped")
                continue
            rows.append((name, ex_id, label, lsk, lcs, goal_sets, goal_value))
        p.ladders.append((ladder, sk, cs, rows))
    return p


def show(p):
    for sql in p.columns:
        print(f"  {sql}")
    for _, old, new, _, _ in p.renames:
        print(f"  rename {old} -> {new}")
    for name, group, timed, sk, cs, icon in p.inserts:
        print(f"  add {name} ({group}) - SK: {sk} / CS: {cs}")
    for name, sk, cs in p.names:
        print(f"  names of {name}: SK {sk} / CS {cs}")
    for src, dst, _, rows in p.moves:
        print(f"  move {len(rows)} sets {src} -> {dst}")
    if p.bands:
        print(f"  band_kg on {len(p.bands)} sets (from the colours in their notes)")
    for _, name in p.hides:
        print(f"  hide {name}")
    for _, workout, name, target, _ in p.plan_rows:
        print(f"  plan {workout}: {name} -> {target}")
    for name, _, mode in p.modes:
        print(f"  band_mode {name}: {mode}")
    for ladder, _, _, rows in p.ladders:
        print(f"  ladder {ladder}: " + " / ".join(f"{i}. {r[2]} ({r[0]})" for i, r in enumerate(rows, 1)))


def apply(conn, p):
    for sql in p.columns:
        conn.execute(sql)
    for ex_id, _, new, sk, cs in p.renames:
        conn.execute("UPDATE exercises SET exercise_name = ?, name_sk = ?, name_cs = ? "
                     "WHERE exercise_id = ?", (new, sk, cs, ex_id))
    new_ids = {}
    for name, group, timed, sk, cs, icon in p.inserts:
        new_ids[name] = conn.execute(
            "INSERT INTO exercises (exercise_name, muscle_group, is_timed, is_deleted, name_sk, "
            "name_cs, icon) VALUES (?, ?, ?, 0, ?, ?, ?)", (name, group, timed, sk, cs, icon)).lastrowid
    for name, sk, cs in p.names:
        conn.execute("UPDATE exercises SET name_sk = ?, name_cs = ? WHERE exercise_name = ?",
                     (sk, cs, name))

    for _, _, dst_id, rows in p.moves:
        # A moved set goes after the target's sets of the same session, so
        # set numbers never collide.
        for entry_id, session_id in rows:
            last = conn.execute("SELECT MAX(set_number) FROM exercise_entries "
                                "WHERE session_id = ? AND exercise_id = ?",
                                (session_id, dst_id)).fetchone()[0]
            own = conn.execute("SELECT set_number FROM exercise_entries WHERE entry_id = ?",
                               (entry_id,)).fetchone()[0]
            number = own if last is None or own > last else last + 1
            conn.execute("UPDATE exercise_entries SET exercise_id = ?, set_number = ? "
                         "WHERE entry_id = ?", (dst_id, number, entry_id))

    for entry_id, band, weight in p.bands:
        conn.execute("UPDATE exercise_entries SET band_kg = ?, weight = ? WHERE entry_id = ?",
                     (band, weight, entry_id))
    for ex_id, _ in p.hides:
        conn.execute("UPDATE exercises SET is_deleted = 1 WHERE exercise_id = ?", (ex_id,))
    for we_id, _, _, _, target_id in p.plan_rows:
        conn.execute("UPDATE workout_exercises SET exercise_id = ? WHERE workout_exercise_id = ?",
                     (target_id, we_id))
    for _, ex_id, mode in p.modes:
        conn.execute("UPDATE exercises SET band_mode = ? WHERE exercise_id = ?",
                     (mode, new_ids.get(ex_id, ex_id)))
    for ladder, sk, cs, rows in p.ladders:
        pid = conn.execute("INSERT INTO progressions (name, name_sk, name_cs) VALUES (?, ?, ?)",
                           (ladder, sk, cs)).lastrowid
        for level, (name, ex_id, label, lsk, lcs, goal_sets, goal_value) in enumerate(rows, 1):
            ex_id = new_ids.get(ex_id, ex_id)
            conn.execute("INSERT INTO progression_levels (progression_id, exercise_id, level, label, "
                         "label_sk, label_cs, goal_sets, goal_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (pid, ex_id, level, label, lsk, lcs, goal_sets, goal_value))


def main():
    do_apply = "--apply" in sys.argv[1:]
    if not os.path.exists(DB_PATH):
        sys.exit(f"No database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'progressions'").fetchone():
            sys.exit("No progressions table - run temp/add_progression_tables.py first.")
        p = make_plan(conn)
        show(p)
        if p.empty():
            print("Nothing to do.")
            return
        if not do_apply:
            print("\nDry run. Run with --apply to do it.")
            return
        conn.close()
        backup = f"{DB_PATH}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(DB_PATH, backup)
        print(f"\nBackup: {backup}")
        conn = sqlite3.connect(DB_PATH)
        with conn:
            apply(conn, p)
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
