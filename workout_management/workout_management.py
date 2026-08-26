import inspect
import matplotlib.dates
import base64
import io
import pandas as pd
from db_setup import db
from flask_login import current_user
from models.models import (
    Users,
    Exercise,
    WorkoutPlan,
    WorkoutExercises,
    Sessions,
    ExerciseEntries,
    Mesocycles,
    SessionMesocycles,
)
from sqlalchemy import (
    MetaData,
    and_,
    func,
    create_engine,
    desc,
    delete,
)
from sqlalchemy.exc import SQLAlchemyError
from flask import request
from datetime import datetime, date, timedelta
from matplotlib.figure import Figure
from io import BytesIO


class WorkoutManagement:
    def __init__(self):
        pass

    def current_user_id_db(self):
        user = Users.query.filter_by(username=current_user.username).first()
        return user.user_id

    def find_users_weeks(self):
        user = Users.query.filter_by(username=current_user.username).first()
        if not user:
            print("User not found.")
            return None, None, None  # Handle case where user is not found

        user_id_db = user.user_id
        # Retrieve last mesocycle's data from my table
        last_meso_query = (
            db.session.query(Mesocycles)
            .filter(Mesocycles.user_id == user_id_db)
            .order_by(Mesocycles.mesocycle_id.desc())
            .first()
        )

        per_week_db = (
            db.session.query(Mesocycles.workouts_per_week)
            .filter(Mesocycles.user_id == user_id_db)
            .order_by(Mesocycles.mesocycle_id.desc())
            .first()
        )

        if (
            per_week_db and per_week_db[0]
        ):  # Check if per_week_db exists and contains a value
            last_workouts = (
                WorkoutPlan.query.filter(
                    WorkoutPlan.user_id == user_id_db,
                    WorkoutPlan.mesocycle_id == last_meso_query.mesocycle_id,
                    WorkoutPlan.workout_name.isnot(None),
                    WorkoutPlan.workout_name != "c",
                )
                .order_by(desc(WorkoutPlan.created_at))
                .limit(per_week_db[0])
                .all()
            )
            # print(f"Last workouts: {last_workouts}")

            try:
                last_workouts_id = (
                    db.session.query(WorkoutPlan.workout_id)
                    .filter(
                        WorkoutPlan.workout_name != "c",
                        WorkoutPlan.user_id == user_id_db,
                        WorkoutPlan.mesocycle_id == last_meso_query.mesocycle_id,
                        WorkoutPlan.workout_name.isnot(None),
                    )
                    .order_by(WorkoutPlan.created_at.desc())
                    .limit(per_week_db[0])
                    .all()
                )

                workouts_id = (
                    [x[0] for x in last_workouts_id] if last_workouts_id else []
                )
            except Exception as e:
                workouts_id = []
                db.session.rollback()

            workout_names_in_db = [workout.workout_name for workout in last_workouts]

            return per_week_db[0], workout_names_in_db, workouts_id

        return None, None, None

    def exercises_for_jinja(self, jinja_exercises, weekly, workouts_id):
        """Fill jinja_exercises[day] with that day's exercises, in display order.

        The ORDER BY is the point. This used to be a bare filter_by, so
        /create_workout rendered whatever order the database happened to hand
        back (insertion order in practice) while training_session sorted by
        order_in_workout via _workout_exercises_ordered(). The two agreed by
        luck. As soon as rows can be reordered they stop agreeing, so both
        paths now read the same sort. workout_exercise_id is the tie-break,
        which keeps the ordering total even if two rows share a number.

        Each row carries its own workout_exercise_id as "id". The template
        names its form fields after it, so a save identifies a row by primary
        key instead of by its position on the page - see overwrite_exercise().

        The exercise name is joined in rather than looked up row by row: that
        cost one extra SELECT per exercise per page load.
        """
        for x in range(weekly):
            rows = (
                db.session.query(
                    WorkoutExercises.workout_exercise_id,
                    Exercise.exercise_name,
                    WorkoutExercises.prescribed_sets,
                    WorkoutExercises.rest_period,
                )
                .join(Exercise, Exercise.exercise_id == WorkoutExercises.exercise_id)
                .filter(WorkoutExercises.workout_id == workouts_id[x])
                .order_by(
                    WorkoutExercises.order_in_workout.asc(),
                    WorkoutExercises.workout_exercise_id.asc(),
                )
                .all()
            )

            for workout_exercise_id, exercise_name, sets, pauses in rows:
                jinja_exercises[x].append(
                    {
                        "id": workout_exercise_id,
                        "exercise": exercise_name,
                        "sets": sets,
                        "pauses": pauses,
                    }
                )

    # Default order in list
    # Default dict for exercises: jinja_exercises
    def default_order(self, weekly):
        jinja_exercises = {}
        default_order = []

        for x in range(weekly):
            default_order.append(1)
            jinja_exercises[x] = []

        return default_order, jinja_exercises

    # Overwrite exercises, sets or rest period
    def overwrite_exercise(self, submitted_data, workouts_id):
        """Apply the edits made to rows that already exist in the plan.

        Fields are named after the row's primary key - exercise_<id>,
        sets_<id>, pauses_<id> - so a row is found by that key and never by
        where it sits on the page. The positional scheme this replaces had two
        problems: it sorted the form keys with sorted(), which is
        lexicographic (exercise_0_10 landed before exercise_0_2, wrong from ten
        exercises up, and it renamed the wrong rows), and it resolved rows by
        exercise NAME, so filter_by(workout_id, exercise_id).update() hit every
        copy of a duplicated exercise. Neither could survive rows moving.

        The ids arrive from the browser, so every one of them is checked
        against this user's own workouts before anything is written.
        """
        allowed_workout_ids = {wid for wid in workouts_id if wid is not None}
        if not allowed_workout_ids:
            return

        # {workout_exercise_id: {"exercise": name, "sets": n, "pauses": n}}
        edits = {}
        for key, value in submitted_data.items():
            for prefix, field in (
                ("exercise_", "exercise"),
                ("sets_", "sets"),
                ("pauses_", "pauses"),
            ):
                if not key.startswith(prefix):
                    continue
                raw_id = key[len(prefix):]
                # new_exercise_<day> and new_sets_<day> do not match these
                # prefixes at all; isdigit() catches anything else malformed.
                if raw_id.isdigit():
                    edits.setdefault(int(raw_id), {})[field] = value
                break

        if not edits:
            return

        rows = (
            db.session.query(WorkoutExercises)
            .filter(
                WorkoutExercises.workout_exercise_id.in_(edits.keys()),
                WorkoutExercises.workout_id.in_(allowed_workout_ids),
            )
            .all()
        )

        changed = False
        for row in rows:
            edit = edits[row.workout_exercise_id]

            new_name = (edit.get("exercise") or "").strip()
            if new_name:
                exercise_row = (
                    db.session.query(Exercise.exercise_id)
                    .filter_by(exercise_name=new_name)
                    .first()
                )
                # An unknown name means a typo in the autocomplete box. Leave
                # the row alone rather than blanking a real exercise.
                if exercise_row and exercise_row[0] != row.exercise_id:
                    row.exercise_id = exercise_row[0]
                    changed = True

            for field, column in (
                ("sets", "prescribed_sets"),
                ("pauses", "rest_period"),
            ):
                raw = edit.get(field)
                if raw is None or str(raw).strip() == "":
                    continue
                try:
                    number = int(raw)
                except (TypeError, ValueError):
                    continue
                # Both columns are NOT NULL and a zero of either is nonsense.
                if number > 0 and getattr(row, column) != number:
                    setattr(row, column, number)
                    changed = True

        if not changed:
            return

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"overwrite_exercise: rolling back, {e}")

    def find_workout_name_from_user(
        self, submitted_data, weekly, workout_names
    ) -> None:
        # Save to DB - WorkoutPlan
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        for day in range(weekly):
            workout_name = request.form.get(f"workout_name_{day}", None)

            if workout_name != "":
                workout_names[day] = workout_name
                # Save / rename workout in database
                # Find the corresponding workout by user_id and some identifier like day or created_at
                workout = (
                    WorkoutPlan.query.filter_by(user_id=user_id_db)
                    .order_by(WorkoutPlan.created_at.desc())
                    .offset(day)
                    .first()
                )
                if workout:
                    workout.workout_name = workout_name  # Update workout name
                    db.session.add(workout)

            db.session.commit()
        return workout_names

    # Add exercise to database --- add weekly to arguments
    def add_exercise(self, submitted_data, order, weekly, jinja_exercises, workouts_id):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id
        new_exercise_order = 0
        exercise_count = 0

        # Function to make exercise dict: if no set /values are provided then set default values
        def user_input_or_defualt():
            prescribed_sets_user = submitted_data.get(f"new_sets_{day}", None)
            rest_period_user = submitted_data.get(f"new_pauses_{day}", None)

            rest_period = rest_period_user if rest_period_user else 120
            prescribed_sets = prescribed_sets_user if prescribed_sets_user else 2

            return rest_period, prescribed_sets

        for day in range(weekly):
            user_exe = submitted_data.get(f"new_exercise_{day}", "")

            # Find exercise_id for exercise user have inputed
            exe_id = (
                db.session.query(Exercise).filter_by(exercise_name=user_exe).first()
            )

            if exe_id:

                # Give me last exercise_id from workout_exercises
                exe_in_db = (
                    db.session.query(WorkoutExercises.exercise_id)
                    .filter_by(workout_id=workouts_id[day])
                    .order_by(WorkoutExercises.workout_exercise_id.desc())
                    .all()
                )

                exercise_ids = [exercise_id[0] for exercise_id in exe_in_db]

                if exe_id.exercise_id in exercise_ids:
                    # In this case don't save exercise to db -> maybe give user some info
                    print("I have this exercise in db. Nothing is going to happen.")

                else:
                    print("This exercise is not in db yet. I am saving it now.")

                    rest, sets = user_input_or_defualt()
                    new_exercise_order = self._next_order_in_workout(workouts_id[day])

                    try:
                        new_exercise = WorkoutExercises(
                            order_in_workout=new_exercise_order,
                            exercise_id=exe_id.exercise_id,
                            prescribed_sets=int(sets),
                            rest_period=int(rest),
                            workout_id=workouts_id[day],
                        )
                        db.session.add(new_exercise)
                        db.session.commit()
                    except (SQLAlchemyError, ValueError, TypeError) as e:
                        db.session.rollback()
                        print(f"add_exercise: rolling back, {e}")

        return order

    def delete_exercise(self, submitted_data, workouts_id):
        """Remove the rows whose "Del" checkbox was ticked.

        Fields are remove_<workout_exercise_id>, so the row goes by primary
        key. The old version read the exercise NAME out of the neighbouring
        field and deleted the first row matching it, which picked the wrong
        one whenever a day held the same exercise twice.

        Ownership is checked before the DELETE - the id comes from the browser.
        Order is compacted once per affected workout at the end rather than
        once per deleted row.
        """
        allowed_workout_ids = {wid for wid in workouts_id if wid is not None}
        if not allowed_workout_ids:
            return

        wanted = set()
        for key, value in submitted_data.items():
            if not key.startswith("remove_"):
                continue
            raw_id = key[len("remove_"):]
            # An unticked checkbox is not submitted at all, so presence is
            # most of the test; the truthiness check is belt and braces.
            if raw_id.isdigit() and value:
                wanted.add(int(raw_id))

        if not wanted:
            return

        rows = (
            db.session.query(WorkoutExercises)
            .filter(
                WorkoutExercises.workout_exercise_id.in_(wanted),
                WorkoutExercises.workout_id.in_(allowed_workout_ids),
            )
            .all()
        )
        # Already gone (double submit, stale form) - nothing to do.
        if not rows:
            return

        touched_workouts = {row.workout_id for row in rows}

        try:
            for row in rows:
                db.session.delete(row)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"delete_exercise: rolling back, {e}")
            return

        # Close the holes the deletes just opened, otherwise order_in_workout
        # becomes 1, 3, 4 and anything that walks the sequence breaks.
        for workout_id in touched_workouts:
            self._compact_workout_order(workout_id)

    def reorder_exercises(self, submitted_data, weekly, workouts_id):
        """Apply the order the user dragged the exercise rows into.

        The page submits order_<day> as a comma separated list of
        workout_exercise_id in the order the rows now appear on screen. That is
        the whole protocol - because every row already carries its own primary
        key, the new order is just the sequence of those keys, and nothing here
        has to reason about what moved where.

        Positions are rewritten to a dense 1..N, the same shape
        _compact_workout_order() maintains after a delete. It is a handful of
        UPDATEs against one workout, which is why this needs no schema change
        and no gapped or fractional ranking scheme.

        The ids come from the browser, so a row is only touched if it really
        belongs to the day it was submitted under. Anything else in the list -
        someone else's id, a row deleted in another tab, a repeat, junk - is
        dropped rather than trusted. Rows the list does not mention (added
        since the page was rendered) keep their relative order and go last.

        Run this BEFORE overwrite_exercise() so the rest of the save sees the
        final positions.
        """
        for day in range(weekly):
            if day >= len(workouts_id):
                continue
            workout_id = workouts_id[day]
            if workout_id is None:
                continue

            raw = submitted_data.get(f"order_{day}")
            if not raw:
                continue

            wanted = []
            for chunk in raw.split(","):
                chunk = chunk.strip()
                if chunk.isdigit():
                    value = int(chunk)
                    if value not in wanted:
                        wanted.append(value)
            if not wanted:
                continue

            # Keyed by primary key, but built from the ordered query so the
            # leftovers below keep a sensible relative order.
            rows = {
                row.workout_exercise_id: row
                for row in self._workout_exercises_ordered(workout_id)
            }

            ordered = [rows[we_id] for we_id in wanted if we_id in rows]
            mentioned = {row.workout_exercise_id for row in ordered}
            ordered += [
                row
                for row in rows.values()
                if row.workout_exercise_id not in mentioned
            ]

            changed = False
            for position, row in enumerate(ordered, start=1):
                if row.order_in_workout != position:
                    row.order_in_workout = position
                    changed = True

            if not changed:
                continue

            try:
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"reorder_exercises: rolling back, {e}")

    # For tryining sessions mainly ---------------------------------------
    def add_session_to_db(self, chosen_day_by_user, workouts_id):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        # Map the chosen day to the actual workout_id
        workout_id_hopefully = workouts_id[chosen_day_by_user]

        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        # Check if a session already exists for today
        does_session_exist = (
            db.session.query(Sessions.session_id)
            .filter(
                and_(
                    Sessions.workout_id == workout_id_hopefully,
                    Sessions.user_id == user_id_db,
                    Sessions.session_date >= today,
                    Sessions.session_date < tomorrow,
                )
            )
            .first()
        )

        if does_session_exist:
            print("Sorry, there is already a workout session for today")
        else:
            # No session exists for today; create a new one
            new_session_query = Sessions(
                user_id=user_id_db,
                workout_id=workout_id_hopefully,
                notes="Null",
            )
            db.session.add(new_session_query)
            db.session.commit()  # Commit here to assign session_id

            # Retrieve the assigned session_id
            session_id_result = new_session_query.session_id

            # Also add data to session_mesocycles
            training_day_number_query = (
                db.session.query(Sessions)
                .filter(
                    Sessions.user_id == user_id_db,
                    Sessions.workout_id == workout_id_hopefully,
                )
                .count()
            )

            mesocycle_id_query = (
                db.session.query(Mesocycles.mesocycle_id)
                .filter(
                    Mesocycles.user_id == user_id_db,
                )
                .order_by(desc(Mesocycles.mesocycle_id))
                .first()
            )

            if session_id_result is not None and mesocycle_id_query is not None:
                new_session_mesocycles_query = SessionMesocycles(
                    session_id=session_id_result,
                    mesocycle_id=mesocycle_id_query[0],
                    training_day_number=training_day_number_query,
                )
                db.session.add(new_session_mesocycles_query)
                db.session.commit()

        # Find relevant exercise sets for Jinja
        last_session_query = (
            db.session.query(Sessions.session_id)
            .filter(
                Sessions.user_id == user_id_db,
                func.DATE(Sessions.session_date) == func.current_date(),
                Sessions.workout_id == workout_id_hopefully,
            )
            .order_by(desc(Sessions.session_date))
            .first()
        )

        if last_session_query:
            sets_for_jinja = (
                db.session.query(ExerciseEntries)
                .filter(ExerciseEntries.session_id == last_session_query[0])
                .all()
            )

            return sets_for_jinja

    def find_exercise_id_db(self, exercise):
        find_exercise_query = (
            db.session.query(Exercise.exercise_id)
            .filter(Exercise.exercise_name == exercise)
            .first()
        )

        if find_exercise_query:
            return find_exercise_query
        else:
            return None

    def find_exercise_name_db(self, id):
        find_exercise_query = (
            db.session.query(Exercise.exercise_name)
            .filter(Exercise.exercise_id == id)
            .first()
        )

        if find_exercise_query:
            return find_exercise_query
        else:
            return None

    # ------------------------------------------------------------------
    # Shared query helpers
    #
    # Every helper below is scoped by user_id (directly, or indirectly via a
    # workout_id that was itself resolved from user_id). Nothing here may
    # return another user's rows.
    # ------------------------------------------------------------------

    def _today_bounds(self):
        """Return (start_of_today, start_of_tomorrow) as datetimes."""
        today = datetime.combine(date.today(), datetime.min.time())
        return today, today + timedelta(days=1)

    def _last_mesocycle_id(self, user_id):
        """The user's most recent mesocycle, which is the only one you train in."""
        row = (
            db.session.query(Mesocycles.mesocycle_id)
            .filter(Mesocycles.user_id == user_id)
            .order_by(desc(Mesocycles.mesocycle_id))
            .first()
        )
        return row[0] if row else None

    def _user_workout_ids(self, user_id, chosen_day):
        """All workout_ids this user has under the given name, across ALL mesocycles.

        READ ONLY - this is the history lane. A workout name is re-created for
        every mesocycle, so the same name maps to several workout_ids over time
        and older ones still hold the numbers progressive overload builds on.

        Never write through this. Use _current_workout_id for that, otherwise a
        set can land in last mesocycle's plan.
        """
        rows = (
            db.session.query(WorkoutPlan.workout_id)
            .filter(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.workout_name == chosen_day,
            )
            .order_by(desc(WorkoutPlan.created_at), desc(WorkoutPlan.workout_id))
            .all()
        )
        return [row[0] for row in rows]

    def _current_workout_id(self, user_id, chosen_day):
        """The workout_id to WRITE to for this day name, or None.

        Restricted to the user's latest mesocycle, because that is the only one
        the training session is allowed to touch. Within that mesocycle the
        newest plan wins - which is also what makes custom "c" days work, since
        those create a fresh plan every day.
        """
        query = db.session.query(WorkoutPlan.workout_id).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.workout_name == chosen_day,
        )

        mesocycle_id = self._last_mesocycle_id(user_id)
        if mesocycle_id is not None:
            query = query.filter(WorkoutPlan.mesocycle_id == mesocycle_id)
        # A user with no mesocycle at all has no "current" one to be confined
        # to, so fall back to their newest plan of that name rather than
        # returning nothing and dead-ending the page.

        row = query.order_by(
            desc(WorkoutPlan.created_at), desc(WorkoutPlan.workout_id)
        ).first()
        return row[0] if row else None

    def _todays_session_id(self, user_id, workout_id, create=False):
        """session_id of this user's session for today, optionally creating it."""
        today, tomorrow = self._today_bounds()

        existing = (
            db.session.query(Sessions.session_id)
            .filter(
                Sessions.user_id == user_id,
                Sessions.workout_id == workout_id,
                Sessions.session_date >= today,
                Sessions.session_date < tomorrow,
            )
            .order_by(desc(Sessions.session_id))
            .first()
        )
        if existing:
            return existing[0]

        if not create:
            return None

        try:
            new_session = Sessions(
                user_id=user_id, workout_id=workout_id, notes="Null"
            )
            db.session.add(new_session)
            db.session.commit()
            return new_session.session_id
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"_todays_session_id: could not create session: {e}")
            return None

    def _previous_session_ids(self, user_id, workout_ids, exclude_session_id=None):
        """This user's sessions for the given workouts, newest first."""
        if not workout_ids:
            return []

        query = db.session.query(Sessions.session_id).filter(
            Sessions.user_id == user_id,
            Sessions.workout_id.in_(workout_ids),
        )
        if exclude_session_id is not None:
            query = query.filter(Sessions.session_id != exclude_session_id)

        rows = query.order_by(
            desc(Sessions.session_date), desc(Sessions.session_id)
        ).all()
        return [row[0] for row in rows]

    def _workout_exercises_ordered(self, workout_id):
        """This workout's exercises lined up in display order.

        workout_exercise_id is the tie-break, so even if two rows share an
        order_in_workout the ordering is still total and stable.
        """
        return (
            db.session.query(WorkoutExercises)
            .filter(WorkoutExercises.workout_id == workout_id)
            .order_by(
                WorkoutExercises.order_in_workout.asc(),
                WorkoutExercises.workout_exercise_id.asc(),
            )
            .all()
        )

    def _next_order_in_workout(self, workout_id):
        """1-based order_in_workout for an exercise appended to this workout.

        Uses MAX, not COUNT: after a deletion COUNT is lower than the highest
        order in use, which hands the new row a number that already exists.
        """
        highest = (
            db.session.query(func.max(WorkoutExercises.order_in_workout))
            .filter(WorkoutExercises.workout_id == workout_id)
            .scalar()
        )
        return (highest or 0) + 1

    def _compact_workout_order(self, workout_id):
        """Renumber a workout's exercises to a gapless 1..N, keeping their order.

        Deleting a row leaves a hole (1, 3, 4). Nothing reads order_in_workout
        expecting holes, so close them as soon as they appear.
        """
        ordered = self._workout_exercises_ordered(workout_id)

        changed = False
        for position, row in enumerate(ordered, start=1):
            if row.order_in_workout != position:
                row.order_in_workout = position
                changed = True

        if changed:
            try:
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"_compact_workout_order: rolling back, {e}")
                return False
        return changed

    # ------------------------------------------------------------------
    # Picking up where you left off
    #
    # The browser session can vanish mid-workout (phone browser evicting it,
    # or just logging out). These let the page re-choose a sensible day and
    # exercise from the database instead of showing an empty dropdown.
    # ------------------------------------------------------------------

    def _rotation_days(self, user_id):
        """Current mesocycle's workout days as [(workout_id, name)], creation order.

        find_users_weeks (and therefore the dropdown) takes the newest N days
        by created_at DESC. We take the same N, then flip them so index 0 is
        the day you built first - that is the order you actually rotate in.
        Custom ("c") and intuitive days are not part of the rotation.
        """
        last_meso = (
            db.session.query(Mesocycles.mesocycle_id, Mesocycles.workouts_per_week)
            .filter(Mesocycles.user_id == user_id)
            .order_by(desc(Mesocycles.mesocycle_id))
            .first()
        )
        if not last_meso or not last_meso[1]:
            return []

        mesocycle_id, per_week = last_meso[0], last_meso[1]

        newest_first = (
            db.session.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.mesocycle_id == mesocycle_id,
                WorkoutPlan.workout_name.isnot(None),
                WorkoutPlan.workout_name != "c",
                ~WorkoutPlan.workout_name.like("%_intuitive"),
            )
            .order_by(desc(WorkoutPlan.created_at), desc(WorkoutPlan.workout_id))
            .limit(per_week)
            .all()
        )

        return [(w.workout_id, w.workout_name) for w in reversed(newest_first)]

    def _last_session_with_sets(self, user_id, workout_ids, on_date=None):
        """Most recent session that has at least one set logged.

        The join is what enforces "at least one set": add_session_to_db creates
        an empty Sessions row the moment you tap confirm, and an empty row must
        not count as a workout.
        """
        if not workout_ids:
            return None

        query = (
            db.session.query(Sessions)
            .join(ExerciseEntries, ExerciseEntries.session_id == Sessions.session_id)
            .filter(
                Sessions.user_id == user_id,
                Sessions.workout_id.in_(workout_ids),
            )
        )

        if on_date is not None:
            start = datetime.combine(on_date, datetime.min.time())
            query = query.filter(
                Sessions.session_date >= start,
                Sessions.session_date < start + timedelta(days=1),
            )

        return (
            query.order_by(desc(Sessions.session_date), desc(Sessions.session_id))
            .first()
        )

    def _first_exercise_name(self, workout_id):
        """Name of the first exercise in a workout, or None if it has none."""
        ordered = self._workout_exercises_ordered(workout_id)
        if not ordered:
            return None
        row = self.find_exercise_name_db(ordered[0].exercise_id)
        return row[0] if row else None

    def suggest_training_focus(self):
        """(day_name, exercise_name) to preselect when the browser session is empty.

        a) Already logged sets today -> that day, and the exercise you logged
           last, so a mid-workout re-login drops you back where you were.
        b) Nothing logged today -> the day after your last real session in the
           rotation, wrapping a -> b -> c -> a, starting at its first exercise.

        Returns (None, None) when there is nothing sensible to suggest.
        """
        user_id = self.current_user_id_db()

        rotation = self._rotation_days(user_id)
        if not rotation:
            return None, None

        workout_ids = [workout_id for workout_id, _ in rotation]
        names_by_id = {workout_id: name for workout_id, name in rotation}

        # a) Mid-workout: resume today's day and the last exercise touched.
        today_session = self._last_session_with_sets(
            user_id, workout_ids, on_date=date.today()
        )
        if today_session:
            day_name = names_by_id.get(today_session.workout_id)

            last_entry = (
                db.session.query(ExerciseEntries)
                .filter(ExerciseEntries.session_id == today_session.session_id)
                .order_by(desc(ExerciseEntries.entry_id))
                .first()
            )

            exercise_name = None
            if last_entry:
                still_in_workout = {
                    row.exercise_id
                    for row in self._workout_exercises_ordered(today_session.workout_id)
                }
                # An exercise removed from the plan mid-mesocycle would not be
                # selectable in the dropdown, so do not offer it.
                if last_entry.exercise_id in still_in_workout:
                    row = self.find_exercise_name_db(last_entry.exercise_id)
                    exercise_name = row[0] if row else None

            if exercise_name is None:
                exercise_name = self._first_exercise_name(today_session.workout_id)

            return day_name, exercise_name

        # b) New day: step to the next day in the rotation.
        last_session = self._last_session_with_sets(user_id, workout_ids)

        if last_session:
            current_index = next(
                (
                    i
                    for i, (workout_id, _) in enumerate(rotation)
                    if workout_id == last_session.workout_id
                ),
                None,
            )
            next_index = 0 if current_index is None else (current_index + 1) % len(rotation)
        else:
            # Never trained in this mesocycle - start at the beginning.
            next_index = 0

        next_workout_id, next_day_name = rotation[next_index]
        return next_day_name, self._first_exercise_name(next_workout_id)

    def _last_entry(self, session_id, exercise_id):
        """Most recently logged set of one exercise inside one session.

        Ordered by set_number then entry_id so it survives equal/missing set
        numbers. Ordering by exercise_id here would be meaningless - it is
        already pinned by the filter.
        """
        return (
            db.session.query(ExerciseEntries)
            .filter(
                ExerciseEntries.session_id == session_id,
                ExerciseEntries.exercise_id == exercise_id,
            )
            .order_by(desc(ExerciseEntries.set_number), desc(ExerciseEntries.entry_id))
            .first()
        )

    def _heaviest_entry(self, session_id, exercise_id):
        """Top set of one exercise inside one session (weight, then reps)."""
        return (
            db.session.query(ExerciseEntries)
            .filter(
                ExerciseEntries.session_id == session_id,
                ExerciseEntries.exercise_id == exercise_id,
            )
            .order_by(
                desc(ExerciseEntries.weight),
                desc(ExerciseEntries.reps),
                desc(ExerciseEntries.entry_id),
            )
            .first()
        )

    def _next_set_number(self, session_id, exercise_id):
        """1-based set number for the next set of this exercise in this session."""
        done = (
            db.session.query(func.count(ExerciseEntries.entry_id))
            .filter(
                ExerciseEntries.session_id == session_id,
                ExerciseEntries.exercise_id == exercise_id,
            )
            .scalar()
        )
        return (done or 0) + 1

    def add_set_to_db(self, submitted_data, exercise, chosen_day) -> dict:
        """Append a manually entered set to today's session for `chosen_day`."""
        if exercise is None:
            return None

        user_id_db = self.current_user_id_db()

        exe_id = self.find_exercise_id_db(exercise)
        if not exe_id:
            print(f"add_set_to_db: unknown exercise '{exercise}'")
            return None

        # Latest mesocycle only - a set must never land in an old plan.
        current_workout_id = self._current_workout_id(user_id_db, chosen_day)
        if current_workout_id is None:
            print(
                f"add_set_to_db: no workout named '{chosen_day}' in this user's "
                f"current mesocycle"
            )
            return None

        # Sets are only ever written into TODAY's session, which is also the
        # only session the training page renders. Same rule as repeat_set.
        session_id = self._todays_session_id(
            user_id_db, current_workout_id, create=True
        )
        if session_id is None:
            return None

        try:
            exercise_entry_add = ExerciseEntries(
                session_id=session_id,
                exercise_id=exe_id[0],
                set_number=self._next_set_number(session_id, exe_id[0]),
                reps=int(submitted_data.get("reps", 0)),
                weight=float(submitted_data.get("kg", 0.0)),
                rpe=int(submitted_data.get("rpe", 0)),
                notes=submitted_data.get("notes", ""),
            )
            db.session.add(exercise_entry_add)
            db.session.commit()
            return exercise_entry_add
        except (SQLAlchemyError, ValueError, TypeError) as e:
            db.session.rollback()
            print(f"add_set_to_db: rolling back, {e} (line {inspect.currentframe().f_lineno})")
            return None

    def repeat_set(self, chosen_exercise, workout_id, chosen_day):
        """Append a copy of a previous set for `chosen_exercise` to today's session.

        Precedence:
          1. If this exercise already has sets in TODAY's session, copy the
             last one (highest set_number). This is the normal in-workout case.
          2. Otherwise fall back to the HEAVIEST set of the most recent earlier
             session that contains this exercise - the right anchor to start
             from for progressive overload.

        Everything is scoped to the logged-in user: workout_ids are resolved
        from user_id, and every session query filters on user_id as well.
        """
        if not chosen_exercise:
            return None

        user_id = self.current_user_id_db()

        exercise_row = self.find_exercise_id_db(chosen_exercise)
        if not exercise_row:
            print(f"repeat_set: unknown exercise '{chosen_exercise}'")
            return None
        exercise_id = exercise_row[0]

        # WRITE target: latest mesocycle only.
        current_workout_id = self._current_workout_id(user_id, chosen_day)
        if current_workout_id is None:
            print(
                f"repeat_set: no workout named '{chosen_day}' in this user's "
                f"current mesocycle"
            )
            return None

        # READ history: deliberately spans older mesocycles, so the first
        # session of a new mesocycle still has numbers to build on.
        history_workout_ids = self._user_workout_ids(user_id, chosen_day)

        # 1. Resolve the TARGET session first - today's, created if missing.
        target_session_id = self._todays_session_id(
            user_id, current_workout_id, create=True
        )
        if target_session_id is None:
            return None

        # 2. Prefer the last set already logged today for this exercise.
        source_entry = self._last_entry(target_session_id, exercise_id)

        # 3. Fallback: heaviest set from the most recent earlier session.
        if source_entry is None:
            for previous_session_id in self._previous_session_ids(
                user_id, history_workout_ids, exclude_session_id=target_session_id
            ):
                source_entry = self._heaviest_entry(previous_session_id, exercise_id)
                if source_entry is not None:
                    break

        if source_entry is None:
            # Exercise never logged by this user - nothing to copy.
            return None

        # set_number is counted on the TARGET session, not the source one.
        try:
            new_entry = ExerciseEntries(
                session_id=target_session_id,
                exercise_id=exercise_id,
                set_number=self._next_set_number(target_session_id, exercise_id),
                reps=source_entry.reps,
                weight=source_entry.weight,
                rpe=source_entry.rpe,
                notes="",
            )
            db.session.add(new_entry)
            db.session.commit()
            return new_entry
        except SQLAlchemyError as e:
            db.session.rollback()
            print(
                f"repeat_set: rolling back, {e} "
                f"(line {inspect.currentframe().f_lineno})"
            )
            return None

    def jinja_sets_function(self, chosen_day, chosen_exercise):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        if chosen_exercise:
            exercise_id = self.find_exercise_id_db(chosen_exercise)[0]
        else:
            return None

        if not exercise_id:
            print(f"Exercise '{chosen_exercise}' not found.")
            return None

        workout_id_from_db = (
            db.session.query(WorkoutPlan.workout_id)
            .filter(
                WorkoutPlan.workout_name == chosen_day,
                WorkoutPlan.user_id == user_id_db,
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )

        if workout_id_from_db:
            today = datetime.combine(date.today(), datetime.min.time())
            tomorrow = today + timedelta(days=1)

            if chosen_day != "c":
                desired_session = (
                    db.session.query(Sessions.session_id)
                    .filter(
                        Sessions.user_id == user_id_db,
                        Sessions.workout_id == workout_id_from_db[0],
                        Sessions.session_date >= today,
                        Sessions.session_date < tomorrow,
                    )
                    .first()
                )
            else:
                desired_session = (
                    db.session.query(Sessions.session_id)
                    .filter(
                        Sessions.user_id == user_id_db,
                        Sessions.workout_id == "c",
                        Sessions.session_date >= today,
                        Sessions.session_date < tomorrow,
                    )
                    .first()
                )

            if desired_session:
                try:
                    relevant_exercise_sets = (
                        db.session.query(ExerciseEntries)
                        .filter(
                            ExerciseEntries.session_id == desired_session[0],
                            ExerciseEntries.exercise_id == exercise_id,
                        )
                        .all()
                    )

                    return relevant_exercise_sets
                except Exception as e:
                    print(f"Exception in jinja_sets_function: {e}")
                    db.session.rollback()  # Rollback the session
                    return None

            else:
                return None
        else:
            print("Workout ID not found.")
            return None

    def delete_set(self, submitted_data):
        try:
            # Check if 'delete' key exists and if it contains values
            if "delete" in submitted_data:
                # Retrieve the IDs to delete (assuming it's a list of entry IDs)
                entry_ids_to_delete = (
                    submitted_data.getlist("delete")
                    if isinstance(submitted_data["delete"], list)
                    else [submitted_data["delete"]]
                )

                # Execute the delete statement using SQLAlchemy
                stmt = delete(ExerciseEntries).where(
                    ExerciseEntries.entry_id.in_(entry_ids_to_delete)
                )
                db.session.execute(stmt)
                db.session.commit()
        except KeyError:
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(f"Error during deletion: {e}")

    def exercise_preview(
        self, workout_id, workout_key, chosen_exercise, chosen_day_by_user, workouts_id
    ):
        user_id_db = self.current_user_id_db()
        preview = {
            "exercise": None,
            "sets": None,
            "reps": None,
            "weight": None,
            "rpe": None,
            "notes": None,
            "done": None,
        }
        preview_data = []

        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        if workout_id and workout_key is not None:
            # Same sort as /create_workout and the exercise dropdown, so the
            # preview lists the workout in the order it is actually trained.
            select_all_exercises = self._workout_exercises_ordered(
                workout_id[workout_key]
            )

            # Find last session ID -> if not, preview will be all none
            last_session_id = (
                db.session.query(Sessions)
                .filter(Sessions.user_id == user_id_db)
                .order_by(desc(Sessions.session_id))
                .first()
            )
            if last_session_id:
                if select_all_exercises:
                    # Populate dict with exercises
                    for exers in select_all_exercises:
                        exercise_name = self.find_exercise_name_db(exers.exercise_id)[0]

                        # Fetch the latest ExerciseEntries for the current exercise
                        latest_entry = (
                            db.session.query(ExerciseEntries)
                            .filter(ExerciseEntries.exercise_id == exers.exercise_id)
                            .order_by(desc(ExerciseEntries.entry_id))
                            .first()
                        )

                        # Map the chosen day to the actual workout_id
                        workout_id_hopefully = workouts_id[chosen_day_by_user]

                        # Check if a session already exists for today
                        try:
                            today_session = (
                                db.session.query(Sessions.session_id)
                                .filter(
                                    and_(
                                        Sessions.workout_id == workout_id_hopefully,
                                        Sessions.user_id == user_id_db,
                                        Sessions.session_date >= today,
                                        Sessions.session_date < tomorrow,
                                    )
                                )
                                .first()[0]
                            )
                        except TypeError as e:
                            db.session.rollback()
                            today_session = None

                        done = None

                        if latest_entry and today_session:
                            if latest_entry.session_id != today_session:
                                """print(latest_entry.session_id, ' : ', today_session)
                                print("We are green bro")"""
                                pass
                            else:
                                """print(latest_entry.session_id, ' : ', today_session)
                                print("We are not green bro")"""
                                done = "yes"
                        else:
                            pass

                        # Populate the preview entry with data from the latest_entry or default values
                        preview_entry = {
                            "exercise": exercise_name,
                            "sets": exers.prescribed_sets,
                            "reps": (
                                latest_entry.reps
                                if latest_entry and latest_entry.reps is not None
                                else 0
                            ),
                            "weight": (
                                latest_entry.weight
                                if latest_entry and latest_entry.weight is not None
                                else 0
                            ),
                            "rpe": (
                                latest_entry.rpe
                                if latest_entry and latest_entry.rpe is not None
                                else 0
                            ),
                            "notes": (
                                latest_entry.notes
                                if latest_entry and latest_entry.notes
                                else ""
                            ),
                            "done": done,
                        }

                        preview_data.append(preview_entry)

                    return preview_data

                else:

                    return {None: None}
            else:
                for exers in select_all_exercises:
                    exercise_name = self.find_exercise_name_db(exers.exercise_id)[0]

                    if exercise_name and exers.prescribed_sets:
                        preview_entry = {
                            "exercise": exercise_name,
                            "sets": exers.prescribed_sets,
                            "reps": 0,
                            "weight": 0,
                            "rpe": None,
                            "notes": None,
                            "done": None,
                        }
                        preview_data.append(preview_entry)
                return preview_data

    # Modify sets which user already saved
    def modify_set(self, submitted_data):
        for key, value in submitted_data.items():
            if key.startswith("update_"):
                entry_id = key.split("_")[-1]

                reps = submitted_data.get(f"update_reps_{entry_id}", None)
                weight = submitted_data.get(f"update_weight_{entry_id}", None)
                rpe = submitted_data.get(f"update_rpe_{entry_id}", None)
                notes = submitted_data.get(f"update_notes_{entry_id}", None)

                entry = db.session.get(ExerciseEntries, entry_id)
                if value and entry:
                    try:
                        entry.reps = reps if reps else entry.reps
                        entry.weight = weight if weight else entry.weight
                        entry.rpe = rpe if rpe else entry.rpe
                        entry.notes = notes if notes else entry.notes

                        db.session.commit()
                    except Exception as e:
                        print(f"Changing your set data failed because of {e}")
                        db.session.rollback()

    def sets_to_do(self, chosen_exercise, chosen_day):
        current_user_id = self.current_user_id_db()
        # Exercise id
        try:
            exercise_id = self.find_exercise_id_db(chosen_exercise)[0]
        except Exception as e:
            exercise_id = None
            print(f"exercise_id is None probably: {e}")

        if exercise_id:
            workout_id = (
                db.session.query(WorkoutPlan.workout_id)
                .filter(
                    WorkoutPlan.user_id == current_user_id,
                    WorkoutPlan.workout_name == chosen_day,
                )
                .order_by(desc(WorkoutPlan.created_at))
                .first()
            )

            if workout_id:
                # Search workout_exercise_id for prescribed sets
                specific_exercise = (
                    db.session.query(WorkoutExercises)
                    .filter(
                        WorkoutExercises.workout_id == workout_id[0],
                        WorkoutExercises.exercise_id == exercise_id,
                    )
                    .first()
                )

                if specific_exercise:
                    return specific_exercise.prescribed_sets
                else:
                    return None

    def current_exercise_info(self, chosen_exercise, chosen_day):
        current_user_id = self.current_user_id_db()
        # Exercise id
        try:
            exercise_id = self.find_exercise_id_db(chosen_exercise)[0]
        except Exception as e:
            exercise_id = None
            print(f"exercise_id is None probably: {e}")

        if exercise_id:
            previous_exercise_entry = (
                db.session.query(ExerciseEntries)
                .join(Sessions, ExerciseEntries.session_id == Sessions.session_id)
                .filter(
                    ExerciseEntries.exercise_id == exercise_id,
                    Sessions.user_id == current_user_id,
                )
                .order_by(
                    desc(ExerciseEntries.session_id),
                    desc(ExerciseEntries.weight),
                    desc(ExerciseEntries.reps),
                )
                .first()
            )

            # Get the heaviest weight for the exercise in the last session
            # Ensure previous_exercise_entry exists
            if previous_exercise_entry:
                # Get the heaviest weight entry for that session and exercise
                heaviest_weight_entry = (
                    db.session.query(ExerciseEntries)
                    .filter(
                        ExerciseEntries.exercise_id
                        == previous_exercise_entry.exercise_id,
                        ExerciseEntries.session_id
                        == previous_exercise_entry.session_id,
                    )
                    .order_by(desc(ExerciseEntries.weight))
                    .first()
                )
            else:
                heaviest_weight_entry = None

            if heaviest_weight_entry:
                return heaviest_weight_entry
            else:
                return None

    def show_tables_to_user(self, current_user) -> dict:
        current_user_id = self.current_user_id_db()

        # Find all workouts and exercises for this user. Return dict
        mesocycle_info = {}
        workout_ids = []

        user_mesocycles = (
            db.session.query(Mesocycles)
            .filter(Mesocycles.user_id == current_user)
            .all()
        )

        for i, x in enumerate(user_mesocycles):
            # Find workout_id and add it to dict.
            #
            # workout_name == "c" is an intuitive-training day, created on the
            # fly by create_custom_workout_plan() and hung off whatever
            # mesocycle happened to be newest at the time. Those are one-off
            # sessions, not part of a plan, so they must not show up as workout
            # days on /workout_plan_page or /progress. find_users_weeks()
            # already excludes them the same way for /create_workout.
            # The sessions and sets recorded against them are untouched - only
            # these plan listings stop showing them.
            workout_id = (
                db.session.query(WorkoutPlan.workout_id)
                .filter(
                    WorkoutPlan.mesocycle_id == x.mesocycle_id,
                    WorkoutPlan.workout_name.isnot(None),
                    WorkoutPlan.workout_name != "c",
                )
                .all()
            )

            if workout_id:
                for work_id in workout_id:
                    workout_ids.append(work_id[0])

                # {i:{meso_id: meso_name, duration: weeks, per_week: times}}
                mesocycle_info[i] = {
                    x.name: x.mesocycle_id,
                    "duration": x.mesocycle_duration_weeks,
                    "per_week": x.workouts_per_week,
                    "workout_ids": workout_ids,
                }

                workout_ids = []

        return mesocycle_info

    def tables_informations(self, chosen_mesocycle: str, mesocycle_info: dict) -> dict:
        # Initialize variables with default values
        mesocycle_id = None
        duration = None
        per_week = None
        workout_ids = None

        workouts_from_db = {}
        # Search and assign mesocycle name to relevant dict
        for key, value in mesocycle_info.items():
            if chosen_mesocycle in value:
                mesocycle_id = value[chosen_mesocycle]
                duration = value.get("duration")
                per_week = value.get("per_week")
                workout_ids = value.get("workout_ids")
                break

        if workout_ids:
            for wid in workout_ids:
                workout_name_db = (
                    db.session.query(WorkoutPlan.workout_name)
                    .filter(
                        WorkoutPlan.workout_id == wid,
                    )
                    .first()
                )
                if workout_name_db:
                    w_name_to_dict = workout_name_db[0]
                    workout_exercises = self._workout_exercises_ordered(wid)

                    # Initialize a dictionary for this workout
                    exercise_dict = {}
                    if workout_exercises:
                        for wex in workout_exercises:
                            try:
                                exercise_name = self.find_exercise_name_db(
                                    wex.exercise_id
                                )[0]
                                exercise_details = {
                                    "rest": wex.rest_period,
                                    "sets": wex.prescribed_sets,
                                }
                                # Add exercise details to the dictionary
                                exercise_dict[exercise_name] = exercise_details
                            except Exception as e:
                                print(f"Could not find your exercise name: {e}")

                    # Add the constructed exercise_dict to the main dictionary under the workout name
                    workouts_from_db[w_name_to_dict] = exercise_dict

        return workouts_from_db

    def workout_day_information(
        self, chosen_mesocycle: str, mesocycle_info: dict
    ) -> dict:
        # Initialize variables with default values
        mesocycle_id = None
        duration = None
        per_week = None
        workout_ids = None

        workouts_from_db = {}
        # Search and assign mesocycle name to relevant dict
        for key, value in mesocycle_info.items():
            if chosen_mesocycle in value:
                mesocycle_id = value[chosen_mesocycle]
                duration = value.get("duration")
                per_week = value.get("per_week")
                workout_ids = value.get("workout_ids")
                break

        if workout_ids:
            for wid in workout_ids:
                workouts_list = []
                workout_name_db = (
                    db.session.query(WorkoutPlan.workout_name)
                    .filter(
                        WorkoutPlan.workout_id == wid,
                    )
                    .first()
                )
                if workout_name_db:
                    w_name_to_dict = workout_name_db[0]
                    workout_exercises = self._workout_exercises_ordered(wid)

                    # print(f"what do we have here{workout_name_db[0]} - {wid}")

                    for exrs in workout_exercises:
                        exercise_name_for_list = self.find_exercise_name_db(
                            exrs.exercise_id
                        )[0]
                        workouts_list.append(exercise_name_for_list)
                    workouts_from_db[w_name_to_dict] = workouts_list

        return workouts_from_db

    # Information about progress prepared for jinja2
    def exercise_progress_data(self, workout_info, chosen_day, mesocycle_name):
        current_user_id = self.current_user_id_db()
        mesocycle_id = (
            db.session.query(Mesocycles.mesocycle_id)
            .filter(
                Mesocycles.name == mesocycle_name, Mesocycles.user_id == current_user_id
            )
            .first()[0]
        )

        result_set = {}

        if chosen_day and mesocycle_id:
            for key, value in workout_info.items():
                if chosen_day in key:
                    # I need to get first exercise user made in his mesocycle and last one -> date, reps weight, rpe
                    workout_id = (
                        db.session.query(WorkoutPlan.workout_id)
                        .filter(
                            WorkoutPlan.user_id == current_user_id,
                            WorkoutPlan.workout_name == key,
                            WorkoutPlan.mesocycle_id == mesocycle_id,
                        )
                        .order_by(desc(WorkoutPlan.created_at))
                        .first()[0]
                    )

                    # Find if workout Name == "c"
                    workout_id_c = (
                        db.session.query(WorkoutPlan)
                        .filter(
                            WorkoutPlan.user_id == current_user_id,
                            WorkoutPlan.workout_name == "c",
                            WorkoutPlan.mesocycle_id == mesocycle_id,
                        )
                        .order_by(desc(WorkoutPlan.created_at))
                        .first()
                    )

                    # First session exercise_entry
                    if workout_id:
                        try:
                            first_session = (
                                db.session.query(Sessions.session_id)
                                .filter(
                                    Sessions.user_id == current_user_id,
                                    Sessions.workout_id == workout_id,
                                )
                                .first()
                            )
                        except:
                            first_session = None
                            print("No data yet bro")
                        all_sessions = (
                            db.session.query(Sessions)
                            .filter(
                                Sessions.user_id == current_user_id,
                                Sessions.workout_id == workout_id,
                            )
                            .all()
                        )

                        # Check if these is custom (c) workout
                        if not all_sessions:
                            all_sessions = (
                                db.session.query(Sessions)
                                .filter(
                                    Sessions.user_id == current_user_id,
                                    Sessions.workout_id == "c",
                                )
                                .all()
                            )

                        exercises_in_workout = self._workout_exercises_ordered(
                            workout_id
                        )

                        if exercises_in_workout:
                            for exrs in exercises_in_workout:
                                exercise_name = self.find_exercise_name_db(
                                    exrs.exercise_id
                                )[0]
                                small_data_list = []

                                for sess in all_sessions:
                                    find_exe = (
                                        db.session.query(ExerciseEntries)
                                        .filter(
                                            ExerciseEntries.session_id
                                            == sess.session_id,
                                            ExerciseEntries.exercise_id
                                            == exrs.exercise_id,
                                        )
                                        .all()
                                    )

                                    for som in find_exe:
                                        # Create a new small_data_set dictionary for each entry
                                        small_data_set = {
                                            "date": f"{sess.session_date.day}.{sess.session_date.month}.{sess.session_date.year}",
                                            "reps": som.reps or 0,
                                            "weight": som.weight or 0,
                                            "rpe": som.rpe or 0,
                                            "notes": som.notes or "",
                                        }
                                        small_data_list.append(small_data_set)

                                # Add the list of exercise data to the result_set
                                result_set[exercise_name] = small_data_list
                            # print(f"result_set : {result_set}")
                            return result_set
        else:
            return {None: None}

    @staticmethod
    def _md_cell(value):
        """Make a value safe to sit inside a markdown table cell."""
        if value is None:
            return ""
        text = str(value).strip()
        # A literal pipe would split the cell and break the table.
        text = text.replace("|", "\\|")
        # Newlines in a note would break the row apart.
        text = " ".join(text.split())
        return text

    def progress_as_markdown(self, progress, chosen_day, chosen_mesocycle):
        """Render the progress page's tables as markdown, ready to paste anywhere.

        Pure formatter: it takes the exact dict that `exercise_progress_data`
        already handed to the template, so what you copy always matches what
        you see. Returns "" when there is nothing to copy, which the template
        uses to hide the button.
        """
        if not progress:
            return ""

        # exercise_progress_data returns {None: None} when nothing is selected.
        real_exercises = {
            name: rows for name, rows in progress.items() if name is not None
        }
        if not real_exercises:
            return ""

        title_bits = [b for b in (chosen_mesocycle, chosen_day) if b]
        lines = []
        if title_bits:
            lines.append(f"# {' - '.join(str(b) for b in title_bits)}")
            lines.append("")

        # Same columns as the table on screen.
        header = "| Date | Reps | Weight | RPE | Notes |"
        divider = "|---|---|---|---|---|"

        for exercise_name, rows in real_exercises.items():
            lines.append(f"## {self._md_cell(exercise_name)}")
            lines.append("")

            if not rows:
                lines.append("_No sets logged yet._")
                lines.append("")
                continue

            lines.append(header)
            lines.append(divider)

            for row in rows:
                lines.append(
                    "| {date} | {reps} | {weight} | {rpe} | {notes} |".format(
                        date=self._md_cell(row.get("date", "")),
                        reps=self._md_cell(row.get("reps", "")),
                        weight=self._md_cell(row.get("weight", "")),
                        rpe=self._md_cell(row.get("rpe", "")),
                        notes=self._md_cell(row.get("notes", "")),
                    )
                )
            lines.append("")

        return "\n".join(lines).strip()

    # AJAX for exercises preview when creating workout
    def fetch_exercise_suggestions(self, search_term):
        exercises = Exercise.query.filter(
            Exercise.exercise_name.ilike(f"%{search_term}%")
        ).all()
        return [exercise.exercise_name for exercise in exercises]

    def get_today_intuitive_traing(self):
        current_user_id = self.current_user_id_db()
        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        today_check_query = (
            db.session.query(WorkoutPlan)
            .filter(
                and_(
                    WorkoutPlan.user_id == current_user_id,
                    WorkoutPlan.created_at >= today,
                    WorkoutPlan.created_at < tomorrow,
                    WorkoutPlan.workout_name.like("%_intuitive"),
                )
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )
        if today_check_query:
            name = today_check_query.workout_name.split("_")[1]
            return name
        else:
            return None

    # Add exercise into workout_exercises
    def create_custom_workout_exercise(self, exercise_name):
        user_id_db = self.current_user_id_db()
        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)
        # Find exercise_id for exercise user have inputed
        exe_id = (
            db.session.query(Exercise).filter_by(exercise_name=exercise_name).first()
        )

        # Find workout id and order in workout
        workout_id_query = (
            db.session.query(WorkoutPlan)
            .filter(
                and_(
                    WorkoutPlan.user_id == user_id_db,
                    WorkoutPlan.created_at >= today,
                    WorkoutPlan.created_at < tomorrow,
                    WorkoutPlan.workout_name == "c",
                )
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )

        if workout_id_query:
            # Check if exercise is in WorkoutExercises table
            exercise_already_in_table = (
                db.session.query(WorkoutExercises)
                .filter(
                    WorkoutExercises.workout_id == workout_id_query.workout_id,
                    WorkoutExercises.exercise_id == exe_id.exercise_id,
                )
                .first()
            )
            if exercise_already_in_table is None:
                order = self._next_order_in_workout(workout_id_query.workout_id)

                new_workout_exercise = WorkoutExercises(
                    workout_id=workout_id_query.workout_id,
                    exercise_id=exe_id.exercise_id,
                    order_in_workout=order,
                    prescribed_sets=2,
                    rest_period=120,
                )

                try:
                    db.session.add(new_workout_exercise)
                    db.session.commit()

                    added_exercise = (
                        db.session.query(WorkoutExercises)
                        .filter(
                            WorkoutExercises.workout_id == workout_id_query.workout_id,
                            WorkoutExercises.exercise_id == exe_id.exercise_id,
                        )
                        .first()
                    )

                    return True
                except Exception as e:
                    db.session.rollback()
                    return False

    # Function to add exercise to database for intuitive training
    def add_intuitive_exercise(self, exercise):
        user_id_db = self.current_user_id_db()

        # Check if there is exercise in database
        exercise_in_db = (
            db.session.query(Exercise)
            .filter(Exercise.exercise_name == exercise)
            .first()
        )

        if exercise_in_db:
            # Create new session
            today = datetime.combine(date.today(), datetime.min.time())
            tomorrow = today + timedelta(days=1)
            workout_id_query = (
                db.session.query(WorkoutPlan)
                .filter(
                    and_(
                        WorkoutPlan.user_id == user_id_db,
                        WorkoutPlan.created_at >= today,
                        WorkoutPlan.created_at < tomorrow,
                        WorkoutPlan.workout_name.like("%_intuitive"),
                    )
                )
                .order_by(desc(WorkoutPlan.created_at))
                .first()
            )

            if workout_id_query:
                # Check if exercise is in WorkoutExercises table
                exercise_already_in_table = (
                    db.session.query(WorkoutExercises)
                    .filter(
                        WorkoutExercises.workout_id == workout_id_query.workout_id,
                        WorkoutExercises.exercise_id == exercise_in_db.exercise_id,
                    )
                    .first()
                )

                if exercise_already_in_table is None:
                    order = self._next_order_in_workout(workout_id_query.workout_id)

                    new_workout_exercise = WorkoutExercises(
                        workout_id=workout_id_query.workout_id,
                        exercise_id=exercise_in_db.exercise_id,
                        order_in_workout=order,
                        prescribed_sets=2,
                        rest_period=90,
                    )

                    try:
                        db.session.add(new_workout_exercise)
                        db.session.commit()

                        added_exercise = (
                            db.session.query(WorkoutExercises)
                            .filter(
                                WorkoutExercises.workout_id
                                == workout_id_query.workout_id,
                                WorkoutExercises.exercise_id
                                == exercise_in_db.exercise_id,
                            )
                            .first()
                        )

                        return self.find_exercise_name_db(added_exercise.exercise_id)[0]
                    except Exception as e:
                        db.session.rollback()
                        print(
                            f"Sorry, but there was some problem adding you exercise into database: {e}"
                        )
                        return None
                else:
                    print(
                        "You already have this exercise in your workout plan so don't be stupid"
                    )
                    return None
            else:
                return None
        else:
            return None

    # Custom workout - check if current day exists
    def check_c_session(self):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        # Help function to determine current day - sessions are valid only for that day
        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        # Check if a session already exists for today
        does_session_exist = (
            db.session.query(Sessions.session_id)
            .filter(
                and_(
                    Sessions.workout_id == "c",
                    Sessions.user_id == user_id_db,
                    Sessions.session_date >= today,
                    Sessions.session_date < tomorrow,
                )
            )
            .first()
        )

        if does_session_exist:
            return True
        else:
            return False

    def create_custom_session(self):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        # Create custom session - 'c' for simple search in DB
        new_session_query = Sessions(
            user_id=user_id_db,
            workout_id="c",
            notes="Null",
        )
        db.session.add(new_session_query)
        db.session.commit()

        # Retrieve the assigned session_id
        session_id_result = new_session_query.session_id

        # Also add data to session_mesocycles
        training_day_number_query = (
            db.session.query(Sessions)
            .filter(
                Sessions.user_id == user_id_db,
                Sessions.session_id == session_id_result,
            )
            .count()
        )

        # Find mmesocycle ID to assign my current session to - I want it to be assigned to user's last mesoc
        mesocycle_id_query = (
            db.session.query(Mesocycles.mesocycle_id)
            .filter(
                Mesocycles.user_id == user_id_db,
            )
            .order_by(desc(Mesocycles.mesocycle_id))
            .first()
        )

        if session_id_result is not None and mesocycle_id_query is not None:
            new_session_mesocycles_query = SessionMesocycles(
                session_id=session_id_result,
                mesocycle_id=mesocycle_id_query[0],
                training_day_number=training_day_number_query,
            )
            db.session.add(new_session_mesocycles_query)
            db.session.commit()

    # Insert custom exercise into workout_exercises
    def create_custom_workout_plan(self):
        # If there is no custom workout for today, just make it happen
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id

        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        mesocycle_id_query = (
            db.session.query(Mesocycles.mesocycle_id)
            .filter(
                Mesocycles.user_id == user_id_db,
            )
            .order_by(desc(Mesocycles.mesocycle_id))
            .first()
        )

        today_workout = (
            db.session.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user_id_db,
                WorkoutPlan.created_at >= today,
                WorkoutPlan.created_at < tomorrow,
                WorkoutPlan.workout_name == "c",
            )
            .first()
        )

        if not today_workout:
            create_custom_workout_day = WorkoutPlan(
                user_id=user_id_db,
                workout_name="c",
                mesocycle_id=mesocycle_id_query[0],
            )
            try:
                db.session.add(create_custom_workout_day)
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Exception line {inspect.currentframe().f_lineno}: {e}")
                return False
        else:
            return False

    # Load into list all custom exercises for this day
    def load_custom_exercises_for_day(self):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id
        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)

        result = []

        today_workout = (
            db.session.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user_id_db,
                WorkoutPlan.created_at >= today,
                WorkoutPlan.created_at < tomorrow,
                WorkoutPlan.workout_name == "c",
            )
            .first()
        )

        if today_workout:
            find_saved_exercises_query = self._workout_exercises_ordered(
                today_workout.workout_id
            )

            for x in find_saved_exercises_query:
                result.append(self.find_exercise_name_db(x.exercise_id)[0])

        return result

    # Load data for each user's exercise - first and last entry
    def exercises_progress(self, exercises_data, period_label=None):
        # Example data set
        dates = []
        weights = []
        reps = []

        # Data for relevant exercise
        for exe in exercises_data:
            dates.append(exe[1])
            weights.append(exe[2])
            reps.append(exe[3])

        # Makeing x axis
        x = dates

        # Figure ple axis
        fig = Figure()
        ax = fig.subplots()
        # Plot the weights
        ax.plot(x, weights, marker="o", linestyle="-", color="blue", label="Reps")

        # Add annotations for reps on each data point
        for i, txt in enumerate(reps):
            if i % 2 == 0:
                ax.annotate(
                    f"{txt}",  # The text to display (e.g., "10 reps")
                    (
                        x[i],
                        weights[i],
                    ),  # The (x, y) coordinates of the point to annotate
                    textcoords="offset points",  # How to interpret xytext
                    xytext=(0, 10),  # Offset text 10 points vertically from the point
                    ha="center",  # Horizontal alignment of the text (center it above the point)
                    fontsize=9,  # Adjust font size if needed
                    color="darkgreen",  # Optional: set a color for the annotation text
                )

        # Customize the plot appearance
        # Read the id off the data, not off the leaked loop variable.
        exercise_name = self.find_exercise_name_db(exercises_data[0][0])[0]
        ax.set_title(
            f"{exercise_name} - {period_label}" if period_label else f"{exercise_name}"
        )
        ax.set_ylabel("Weight (kg)")
        ax.grid(True)

        # Format the x-axis to show dates nicely
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d.%m.%y"))
        fig.autofmt_xdate()  # Automatically format x-axis labels to prevent overlap

        # Add a legend
        ax.legend()

        # Save the figure to a BytesIO buffer
        buf = BytesIO()
        fig.savefig(
            buf, format="png", bbox_inches="tight"
        )  # bbox_inches='tight' prevents labels from being cut off
        buf.seek(0)  # Rewind the buffer to the beginning

        # Encode the image data to base64 for embedding in HTML
        data = base64.b64encode(buf.read()).decode("ascii")

        return data

    # Filter data for graph to create
    def data_for_graph(self):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id
        session_for_user = []

        all_sessions_query = (
            db.session.query(Sessions).filter(Sessions.user_id == user_id_db).all()
        )

        for session in all_sessions_query:
            session_for_user.append(session.session_id)

        if session_for_user:
            best_sets_per_session_and_exercise = (
                db.session.query(
                    ExerciseEntries.exercise_id,
                    Sessions.session_date,  # <-- ADD THIS LINE
                    func.max(ExerciseEntries.weight).label("max_weight"),
                    func.max(ExerciseEntries.reps).label("max_reps"),
                )
                .join(
                    Sessions,
                    ExerciseEntries.session_id
                    == Sessions.session_id,  # <-- ADD THIS LINE
                )
                .filter(ExerciseEntries.session_id.in_(session_for_user))
                .group_by(
                    ExerciseEntries.exercise_id,
                    Sessions.session_date,  # <-- ADD THIS LINE to GROUP BY
                )
                .all()
            )

            if best_sets_per_session_and_exercise:
                return best_sets_per_session_and_exercise
            else:
                return None

    # Data for specific exercise
    # (value, label, days back). None days = no lower bound.
    STATISTICS_RANGES = (
        ("month", "Last month", 30),
        ("3months", "Last 3 months", 91),
        ("halfyear", "Last 1/2 year", 183),
        ("year", "Last year", 365),
        ("all", "All time", None),
    )
    DEFAULT_STATISTICS_RANGE = "all"

    def statistics_range_options(self):
        """[{value, label}] for the range dropdown, in display order."""
        return [{"value": value, "label": label}
                for value, label, _ in self.STATISTICS_RANGES]

    def statistics_range_start(self, period):
        """Earliest session_date to include, or None for no lower bound.

        An unknown or missing period falls back to all time rather than
        silently showing an empty graph.
        """
        days_by_value = {value: days for value, _, days in self.STATISTICS_RANGES}
        days = days_by_value.get(period)
        if days is None:
            return None
        return datetime.combine(date.today(), datetime.min.time()) - timedelta(days=days)

    def statistics_range_label(self, period):
        for value, label, _ in self.STATISTICS_RANGES:
            if value == period:
                return label
        return "All time"

    def statistics_for_exercise(self, chosen_exercise, period=None):
        """Best set per session for one exercise, oldest first.

        `period` is one of STATISTICS_RANGES; anything unrecognised means all time.
        """
        if (
            not chosen_exercise
            or chosen_exercise == "Choose Exercise"
            or chosen_exercise == "You have no Mesocycle yet"
        ):
            return None

        user_id_db = self.current_user_id_db()

        exercise_row = self.find_exercise_id_db(chosen_exercise)
        if not exercise_row:
            return None
        exercise_id_db = exercise_row[0]

        # Scoping by joining Sessions on user_id, rather than pre-loading every
        # session id this user has ever had into an IN (...) list.
        query = (
            db.session.query(
                ExerciseEntries.exercise_id,
                Sessions.session_date,
                func.max(ExerciseEntries.weight).label("max_weight"),
                func.max(ExerciseEntries.reps).label("max_reps"),
            )
            .join(Sessions, ExerciseEntries.session_id == Sessions.session_id)
            .filter(
                Sessions.user_id == user_id_db,
                ExerciseEntries.exercise_id == exercise_id_db,
            )
        )

        range_start = self.statistics_range_start(period)
        if range_start is not None:
            query = query.filter(Sessions.session_date >= range_start)

        best_sets_per_session_and_exercise = (
            query.group_by(ExerciseEntries.exercise_id, Sessions.session_date)
            # Without this the rows come back in whatever order the DB likes,
            # which draws the line graph zig-zagging back and forth in time.
            .order_by(Sessions.session_date.asc())
            .all()
        )

        return best_sets_per_session_and_exercise or None

    # All exercises with at least one entry
    def exercises_ranked_by_use(self):
        """This user's logged exercises, most-used first.

        Ranked by number of sets logged, ties broken alphabetically. Only
        exercises with real ExerciseEntries appear, so every entry in the list
        has an actual graph behind it.

        One grouped query rather than a name lookup per exercise, because this
        runs on every statistics page load.
        """
        user_id = self.current_user_id_db()

        rows = (
            db.session.query(
                Exercise.exercise_name,
                func.count(ExerciseEntries.entry_id).label("sets_logged"),
            )
            .join(
                ExerciseEntries,
                ExerciseEntries.exercise_id == Exercise.exercise_id,
            )
            .join(Sessions, Sessions.session_id == ExerciseEntries.session_id)
            .filter(Sessions.user_id == user_id)
            .group_by(Exercise.exercise_id, Exercise.exercise_name)
            .order_by(desc("sets_logged"), Exercise.exercise_name.asc())
            .all()
        )

        return [{"name": name, "sets": sets_logged} for name, sets_logged in rows]

    def all_exercises_list(self):
        user_id_db = self.current_user_id_db()
        session_for_user = []
        exercise_data = []

        all_sessions_query = (
            db.session.query(Sessions).filter(Sessions.user_id == user_id_db).all()
        )

        for session in all_sessions_query:
            session_for_user.append(session.session_id)

        if session_for_user:
            all_exercises_query = (
                db.session.query(ExerciseEntries)
                .filter(ExerciseEntries.session_id.in_(session_for_user))
                .group_by(ExerciseEntries.exercise_id)
                .all()
            )

            if all_exercises_query:
                for exe in all_exercises_query:
                    exercise_data.append(self.find_exercise_name_db(exe.exercise_id)[0])
                    exercise_data.sort()
                return exercise_data
        else:
            return None

    # Load last 3 sets for chosen exercise
    def last_custom_day(self, exercise):
        user = Users.query.filter_by(username=current_user.username).first()
        user_id_db = user.user_id
        exercise_id = self.find_exercise_id_db(exercise)[0]
        # SELECT last workout FROM  WorkoutPlan
        last_c_work_query = (
            db.session.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == user_id_db)
            .order_by(WorkoutPlan.created_at.desc())
            .first()
        )

        # User's sessions
        user_session_query = (
            db.session.query(Sessions)
            .filter(
                Sessions.user_id == user_id_db,
            )
            .order_by(Sessions.session_date.desc())
            .all()
        )

        session_list = []
        for sess in user_session_query:
            session_list.append(sess.session_id)

        # Find all user's sets
        if session_list:
            relevant_exercise_query = (
                db.session.query(ExerciseEntries)
                .filter(
                    ExerciseEntries.session_id.in_(session_list),
                    ExerciseEntries.exercise_id == exercise_id,
                )
                .order_by(ExerciseEntries.entry_id.desc())
                .limit(3)
            )

            if relevant_exercise_query:
                return relevant_exercise_query
            else:
                return None

    # Create downloadable excel file - download workout plan to excel - this one is done by gemini
    def workout_to_excel(self, data):
        # If no data is provided, return a minimal empty Excel file
        if not data:
            print("No data provided for Excel export. Creating an empty workbook.")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                writer.book.add_worksheet("Workout Plan")
            output.seek(0)
            return output

        output = io.BytesIO()
        # Use xlsxwriter engine for advanced formatting features like merged cells
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("Workout Plan")

            # Define custom cell formats for aesthetics
            title_format = workbook.add_format(
                {
                    "bold": True,
                    "font_size": 14,
                    "align": "center",
                    "valign": "vcenter",
                    "fg_color": "#A9D08E",  # Darker green for workout titles
                    "border": 1,
                    "font_color": "#FFFFFF",  # White text for contrast
                    "text_wrap": True,
                    "num_format": "@",  # Ensure text format
                }
            )
            header_format = workbook.add_format(
                {
                    "bold": True,
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "fg_color": "#D7E4BC",  # Light green background for main headers
                    "border": 1,
                }
            )
            sub_header_format = workbook.add_format(
                {
                    "bold": True,
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "fg_color": "#F2F2F2",  # Light grey background for sub-headers
                    "border": 1,
                }
            )
            data_format = workbook.add_format(
                {
                    "border": 1,
                    "align": "left",  # Align exercise names to the left
                    "valign": "vcenter",
                }
            )
            center_data_format = workbook.add_format(
                {
                    "border": 1,
                    "align": "center",  # Center align 'Total'
                    "valign": "vcenter",
                }
            )
            empty_cell_format = workbook.add_format(
                {
                    "fg_color": "#F2F2F2",  # Grey background for empty input cells
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                }
            )

            current_col_offset = (
                0  # Keeps track of the starting column for each new table
            )
            num_sets_per_exercise = 3  # Number of sets (1. SET, 2. SET, 3. SET)
            cols_per_set = 3  # Columns per set (Reps, Weight, RPE)

            # Iterate through each workout (e.g., 'Upper Body', 'Lower Body')
            for workout_name, exercises in data.items():
                # Calculate the total number of columns for this specific table
                # Exercise (1) + Total (1) + (3 sets * 3 columns/set) + Notes (1) = 12 columns
                total_cols_for_table = (
                    1 + 1 + (num_sets_per_exercise * cols_per_set) + 1
                )

                # 1. Write the workout name title (merged across the table's width)
                # Row 0, spanning from current_col_offset to the end of this table's columns
                worksheet.merge_range(
                    0,
                    current_col_offset,
                    0,
                    current_col_offset + total_cols_for_table - 1,
                    workout_name,
                    title_format,
                )

                # 2. Write the main headers (e.g., 'Exercise', 'Total', '1. SET', 'Notes')
                # These go on Row 1
                worksheet.write_string(1, current_col_offset, "Exercise", header_format)
                worksheet.write_string(
                    1, current_col_offset + 1, "Total", header_format
                )

                # Write merged headers for each SET (e.g., '1. SET', '2. SET', '3. SET')
                for i in range(num_sets_per_exercise):
                    # Calculate the starting column for each merged SET header
                    start_set_col = current_col_offset + 2 + (i * cols_per_set)
                    # Merge cells for the SET header (e.g., merge 3 cells for '1. SET')
                    worksheet.merge_range(
                        1,
                        start_set_col,
                        1,
                        start_set_col + cols_per_set - 1,
                        f"{i+1}. SET",
                        header_format,
                    )

                # Write the 'Notes' header
                worksheet.write_string(
                    1,
                    current_col_offset + total_cols_for_table - 1,
                    "Notes",
                    header_format,
                )

                # 3. Write the sub-headers (e.g., 'Reps', 'Weight', 'RPE' under each SET)
                # These go on Row 2
                # Leave the 'Exercise' and 'Total' cells empty in this row
                worksheet.write_string(2, current_col_offset, "", sub_header_format)
                worksheet.write_string(2, current_col_offset + 1, "", sub_header_format)

                for i in range(num_sets_per_exercise):
                    start_sub_col = current_col_offset + 2 + (i * cols_per_set)
                    worksheet.write_string(2, start_sub_col, "Reps", sub_header_format)
                    worksheet.write_string(
                        2, start_sub_col + 1, "Weight", sub_header_format
                    )
                    worksheet.write_string(
                        2, start_sub_col + 2, "RPE", sub_header_format
                    )
                # Leave the 'Notes' cell empty in this row
                worksheet.write_string(
                    2,
                    current_col_offset + total_cols_for_table - 1,
                    "",
                    sub_header_format,
                )

                # 4. Write the exercise data rows
                # Data starts from row 3 (0-indexed)
                data_start_row = 3
                for r_idx, (exercise_name, details) in enumerate(exercises.items()):
                    current_row = data_start_row + r_idx

                    # Write Exercise Name
                    worksheet.write_string(
                        current_row, current_col_offset, exercise_name, data_format
                    )
                    # Write Total Sets (e.g., "3x")
                    worksheet.write_string(
                        current_row,
                        current_col_offset + 1,
                        f"{details['sets']}x",
                        center_data_format,
                    )

                    # Write empty cells for Reps, Weight, RPE for each set
                    for i in range(num_sets_per_exercise):
                        start_empty_col = current_col_offset + 2 + (i * cols_per_set)
                        worksheet.write_string(
                            current_row, start_empty_col, "", empty_cell_format
                        )  # Reps
                        worksheet.write_string(
                            current_row, start_empty_col + 1, "", empty_cell_format
                        )  # Weight
                        worksheet.write_string(
                            current_row, start_empty_col + 2, "", empty_cell_format
                        )  # RPE

                    # Write empty cell for Notes
                    worksheet.write_string(
                        current_row,
                        current_col_offset + total_cols_for_table - 1,
                        "",
                        empty_cell_format,
                    )

                # 5. Adjust column widths for readability
                worksheet.set_column(
                    current_col_offset, current_col_offset, 25
                )  # Exercise column width
                worksheet.set_column(
                    current_col_offset + 1, current_col_offset + 1, 10
                )  # Total column width
                for i in range(num_sets_per_exercise):
                    start_set_col = current_col_offset + 2 + (i * cols_per_set)
                    worksheet.set_column(
                        start_set_col, start_set_col + cols_per_set - 1, 10
                    )  # Reps, Weight, RPE columns
                worksheet.set_column(
                    current_col_offset + total_cols_for_table - 1,
                    current_col_offset + total_cols_for_table - 1,
                    25,
                )  # Notes column width

                # 6. Update the column offset for the next table
                # Add the total columns of the current table plus some spacing (e.g., 2 empty columns)
                current_col_offset += total_cols_for_table + 2

        writer.close()  # Crucial: Close the Excel writer to finalize the file
        output.seek(0)  # Rewind the buffer to the beginning before returning
        return output  # Return the BytesIO object containing the Excel file data

    # Function created for progress page -> set default mesocycle for user's last one in db
    def last_mesocycle_by_default(self) -> str:
        user_id = self.current_user_id_db()
        last_meso_query = (
            db.session.query(Mesocycles)
            .filter(Mesocycles.user_id == user_id)
            .order_by(desc(Mesocycles.mesocycle_id))
            .first()
        )
        return last_meso_query.name

    def user_last_session_id(self, workout_id, chosen_day):
        """(sessions newest-first, workout_id) for this user's current `chosen_day`."""
        user_id = self.current_user_id_db()

        # Was matching workout_name with no user_id filter at all, so another
        # user's plan could satisfy the lookup.
        workout_id_current = self._current_workout_id(user_id, chosen_day)
        if workout_id_current is None:
            return None, None

        # Honour the caller's candidate list when it gives one.
        if workout_id and workout_id_current not in workout_id:
            return None, None

        return (
            db.session.query(Sessions)
            .filter(
                Sessions.user_id == user_id,
                Sessions.workout_id == workout_id_current,
            )
            .order_by(desc(Sessions.session_id))
            .all(),
            workout_id_current,
        )

    # Training session: Button "History"
    def last_exercise_preview(self, chosen_exercise, workout_id, chosen_day):
        user_id = self.current_user_id_db()
        today = datetime.combine(date.today(), datetime.min.time())
        tomorrow = today + timedelta(days=1)
        if not chosen_exercise:
            return None

        # Check if today's session -> If yes -> ignore in user_sessions
        day_check = (
            db.session.query(Sessions.session_id)
            .filter(
                and_(
                    Sessions.user_id == user_id,
                    Sessions.session_date >= today,
                    Sessions.session_date < tomorrow,
                )
            )
            .all()
        )

        today_ids = [s_id for s_id, in day_check]

        exe_id = self.find_exercise_id_db(chosen_exercise)[0]

        if workout_id and chosen_day and exe_id:
            # Simplify -> Find all sessions for current user
            # Create list / object of all user sessions
            if day_check:
                user_sessions = (
                    db.session.query(Sessions)
                    .filter(
                        Sessions.user_id == user_id,
                        Sessions.workout_id != "c",
                        Sessions.session_id.notin_(today_ids),
                    )
                    .order_by(desc(Sessions.session_date))
                    .all()
                )
            else:
                user_sessions = (
                    db.session.query(Sessions)
                    .filter(Sessions.user_id == user_id, Sessions.workout_id != "c")
                    .order_by(desc(Sessions.session_date))
                    .all()
                )
            # Give me nested list of exercises
            if user_sessions:
                # Logic -> iterate session by session and find the last session where the exercise was done
                entries_to_display = None
                for x in user_sessions:
                    entries_to_display_temp = (
                        db.session.query(ExerciseEntries)
                        .filter(
                            ExerciseEntries.exercise_id == exe_id,
                            ExerciseEntries.session_id == x.session_id,
                        )
                        .all()
                    )
                    if entries_to_display_temp:
                        entries_to_display = entries_to_display_temp
                        break

                if entries_to_display:
                    return entries_to_display
                else:
                    return None

            else:
                # No sessions exists for this user
                return None

    def arrow_buttons_next_exercise(self, move: str, chosen_exercise, chosen_day):
        """Name of the exercise one step before/after the current one, or None at the ends.

        Navigates by POSITION in the workout's ordered list, not by arithmetic
        on order_in_workout. A hole left by a deletion (1, 3, 4) or a duplicate
        number (1, 1, 2) therefore cannot break it - "the 2nd item of a 3 item
        list" always exists, whereas "the row numbered 2" may not.
        """
        if not (move and chosen_exercise and chosen_day):
            return None

        if move not in ("previous_day", "next_day"):
            return None

        user_id = self.current_user_id_db()

        # Latest mesocycle only - the arrows must walk the plan you are
        # actually training, not a same-named day from an older mesocycle.
        current_workout_id = self._current_workout_id(user_id, chosen_day)
        if current_workout_id is None:
            return None

        ordered = self._workout_exercises_ordered(current_workout_id)
        if not ordered:
            return None

        exercise_row = self.find_exercise_id_db(chosen_exercise)
        if not exercise_row:
            return None
        exercise_id = exercise_row[0]

        current_index = next(
            (i for i, row in enumerate(ordered) if row.exercise_id == exercise_id),
            None,
        )
        if current_index is None:
            # Current exercise is not in this workout any more (just deleted,
            # or the day was switched underneath us).
            return None

        step = -1 if move == "previous_day" else 1
        target_index = current_index + step

        if target_index < 0 or target_index >= len(ordered):
            # Already at the first / last exercise.
            return None

        name = self.find_exercise_name_db(ordered[target_index].exercise_id)
        return name[0] if name else None
