"""Progression ladders: exercises that are levels of one movement (see
Progression / ProgressionLevel in models/models.py).

Each level is still an exercise of its own; everything here only answers
"which ladder is this exercise in, at what level, and what are its
neighbours". Read once per request (flask.g) - a few dozen rows.

Names follow the same rule as exercise names: the Slovak / Czech ones are
shown to a user who reads exercise names translated (Customization), the
English ones to everyone else.
"""
from flask import g, has_request_context
from flask_login import current_user

from models.db_setup import db
from models.models import Exercise, Progression, ProgressionLevel
from translations.i18n import current_language


def _translated(english, sk, cs):
    if not (has_request_context() and getattr(current_user, "translate_exercises", False)):
        return english
    return {"sk": sk, "cs": cs}.get(current_language()) or english


def _load():
    """({progression_id: ladder}, {exercise_name: level}) - a ladder is
    {"id", "name" (English), "label" (shown), "timed", "levels": [level, ...]}
    and a level {"ladder" (id), "exercise" (English name), "exercise_id",
    "level", "label", "goal_sets", "goal_value"}, levels in order."""
    if has_request_context() and hasattr(g, "progressions"):
        return g.progressions
    ladders = {
        p.progression_id: {"id": p.progression_id, "name": p.name, "timed": False,
                           "label": _translated(p.name, p.name_sk, p.name_cs), "levels": []}
        for p in db.session.query(Progression)
    }
    by_name = {}
    rows = (db.session.query(ProgressionLevel, Exercise.exercise_name, Exercise.is_timed)
            .join(Exercise, Exercise.exercise_id == ProgressionLevel.exercise_id)
            .filter(Exercise.is_deleted.is_(False))
            .order_by(ProgressionLevel.progression_id, ProgressionLevel.level))
    for lv, name, timed in rows:
        ladder = ladders.get(lv.progression_id)
        if ladder is None:
            continue
        level = {"ladder": lv.progression_id, "exercise": name, "exercise_id": lv.exercise_id,
                 "level": lv.level, "label": _translated(lv.label, lv.label_sk, lv.label_cs),
                 "goal_sets": lv.goal_sets, "goal_value": lv.goal_value}
        ladder["levels"].append(level)
        ladder["timed"] = ladder["timed"] or bool(timed)
        by_name[name] = level
    # A ladder with no level left (all deleted) is no ladder.
    ladders = {pid: ladder for pid, ladder in ladders.items() if ladder["levels"]}
    result = (ladders, by_name)
    if has_request_context():
        g.progressions = result
    return result


def ladders():
    """{progression_id: ladder}, see _load()."""
    return _load()[0]


def level_of(exercise_name):
    """The level an exercise is (see _load()), or None when it is in no ladder."""
    return _load()[1].get(exercise_name)


def ladder_of(exercise_name):
    """The ladder an exercise is a level of, or None."""
    level = level_of(exercise_name)
    return ladders().get(level["ladder"]) if level else None


def position(exercise_name):
    """(index in its ladder, number of levels), or None."""
    ladder = ladder_of(exercise_name)
    if not ladder:
        return None
    names = [lv["exercise"] for lv in ladder["levels"]]
    return names.index(exercise_name), len(names)


def sibling_ids(exercise_id):
    """The exercise ids that count as "this exercise" when sets are matched to
    a plan row: every level of its ladder, or just itself."""
    for ladder in ladders().values():
        ids = [lv["exercise_id"] for lv in ladder["levels"]]
        if exercise_id in ids:
            return ids
    return [exercise_id]


def catalog_info():
    """{exercise_name: {"ladder", "ladder_label", "level", "levels", "label",
    "goal"}} for the exercise picker and the Create Workout level stepper."""
    out = {}
    for ladder in ladders().values():
        count = len(ladder["levels"])
        for i, lv in enumerate(ladder["levels"]):
            out[lv["exercise"]] = {
                "ladder": ladder["id"], "ladder_label": ladder["label"], "timed": ladder["timed"],
                "index": i, "levels": count, "label": lv["label"],
                "goal_sets": lv["goal_sets"], "goal_value": lv["goal_value"],
            }
    return out


def neighbours(exercise_name, taken=()):
    """(easier, harder): the English names of the levels just below and just
    above this one, for the level icons in Training Session. Each is None at
    the end of the ladder, or when that level is already another row of the
    same day (`taken`) - one plan day never holds a level twice. None when
    the exercise is in no ladder."""
    ladder = ladder_of(exercise_name)
    if not ladder:
        return None
    names = [lv["exercise"] for lv in ladder["levels"]]
    i = names.index(exercise_name)
    taken = set(taken) - {exercise_name}

    def free(j):
        return names[j] if 0 <= j < len(names) and names[j] not in taken else None

    return free(i - 1), free(i + 1)
