import os
import inspect # Example: print(f"Exception line {inspect.currentframe().f_lineno}: {e}")
from datetime import datetime, date, timedelta

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    DateTime,
    Boolean,
    and_,
    func,
    create_engine,
    select,
    desc,
    delete,
    cast,
    Date
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import FloatField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange

app = Flask(__name__, instance_relative_config=True)
app.secret_key = "thiskeyshouldntbeherebutfornowitisok.1084"

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Database setup
class Base(DeclarativeBase):
    pass

basedir = os.path.abspath(os.path.dirname(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'instance/workout.db')}"
)

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///workout.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=20)

# Create engine so I can work with dynamic tables
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
metadata = MetaData()

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# 1. Users Table
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    age = Column(Integer, unique=False, nullable=False)
    weight = Column(Float, unique=False, nullable=False)
    mesocycles = Column(Integer, unique=False, nullable=True)
    email = Column(String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

    def get_id(self):
        return str(self.user_id)

    def __init__(self, username, password, age, weight, email):
        self.password = password
        self.username = username
        self.age = age
        self.weight = weight
        self.email = email

# 2. Exercises Table
class Exercise(UserMixin, db.Model):
    __tablename__ = "exercises"
    exercise_id = Column(Integer, primary_key=True)
    exercise_name = Column(String(100), unique=True, nullable=False)
    muscle_group = Column(String(100), unique=False, nullable=False)

    def __init__(self, exercise, muscle_group):
        self.exercise_name = exercise
        self.muscle_group = muscle_group

# 3. Workouts Table
class WorkoutPlan(UserMixin, db.Model):
    __tablename__ = "workouts"
    workout_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    workout_name = Column(String(100), unique=False, nullable=True)
    created_at = Column(DateTime, default=func.now())  # current time / date
    mesocycle_id = Column(Integer, db.ForeignKey("mesocycles.mesocycle_id"))

    def __init__(
        self,
        user_id,
        workout_name,
        mesocycle_id
    ):
        self.user_id = user_id
        self.workout_name = workout_name
        self.mesocycle_id = mesocycle_id
        # created_at is not here because SQLAlchemy will take care of it

# 4. WorkoutExercises Table
class WorkoutExercises(UserMixin, db.Model):
    __tablename__ = "workout_exercises"
    workout_exercise_id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    exercise_id = Column(Integer, db.ForeignKey("exercises.exercise_id"))
    order_in_workout = Column(Integer, unique=False, nullable=False)
    prescribed_sets = Column(Integer, unique=False, nullable=False)
    rest_period = Column(Integer, unique=False, nullable=False)
    # deleted = Column(Boolean, nullable=False, default=False)

    def __init__(
        self,
        workout_id,
        exercise_id,
        order_in_workout,
        prescribed_sets,
        rest_period,
    ):
        self.workout_id = workout_id
        self.exercise_id = exercise_id
        self.order_in_workout = order_in_workout
        self.prescribed_sets = prescribed_sets
        self.rest_period = rest_period
        # self.deleted = deleted

# 5. Sessions Table
# High-level information about each workout session, such as the date, user, and overall notes
class Sessions(UserMixin, db.Model):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    session_date = Column(DateTime, default=func.now())
    notes = Column(String(150), unique=False, nullable=True)

    def __init__(self, user_id, workout_id, notes):
        self.user_id = user_id
        self.workout_id = workout_id
        self.notes = notes

# 6. ExerciseEntries Table
class ExerciseEntries(UserMixin, db.Model):
    __tablename__ = "exercise_entries"
    entry_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, db.ForeignKey("sessions.session_id"))
    exercise_id = Column(Integer, db.ForeignKey("exercises.exercise_id"))
    set_number = Column(Integer, unique=False, nullable=False)
    reps = Column(Integer, unique=False, nullable=True)
    weight = Column(Float, unique=False, nullable=True)
    rpe = Column(Float, unique=False, nullable=True)
    notes = Column(String(150), unique=False, nullable=True)

    def __init__(self, session_id, exercise_id, set_number, reps, weight, rpe, notes):
        self.session_id = session_id
        self.exercise_id = exercise_id
        self.set_number = set_number
        self.reps = reps
        self.weight = weight
        self.rpe = rpe
        self.notes = notes

# 7. Mesocycles Table
class Mesocycles(UserMixin, db.Model):
    __tablename__ = "mesocycles"
    mesocycle_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    name = Column(String(100), unique=False, nullable=False)
    mesocycle_duration_weeks = Column(Integer, unique=False, nullable=False)
    workouts_per_week = Column(Integer, unique=False, nullable=False)

    def __init__(self, user_id, mesocycle_duration_weeks, workouts_per_week, name):
        self.user_id = user_id
        self.name = name
        self.mesocycle_duration_weeks = mesocycle_duration_weeks
        self.workouts_per_week = workouts_per_week

# 8. SessionMesocycles Table
# Links sessions to mesocycles, allowing tracking of training days within a mesocycle
class SessionMesocycles(UserMixin, db.Model):
    __tablename__ = "session_mesocycles"
    session_id = Column(Integer, db.ForeignKey("sessions.session_id"), primary_key=True)
    mesocycle_id = Column(
        Integer, db.ForeignKey("mesocycles.mesocycle_id"), primary_key=True
    )
    training_day_number = Column(Integer, unique=False, nullable=False)

    def __init__(self, session_id, mesocycle_id, training_day_number):
        self.session_id = session_id
        self.mesocycle_id = mesocycle_id
        self.training_day_number = training_day_number

@login_manager.user_loader
def load_user(user_id):
    stmt = select(Users).where(Users.user_id == int(user_id))
    return db.session.execute(stmt).scalar_one_or_none()

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), EqualTo("confirm", message="Passwords must match")],
    )
    confirm = PasswordField("Confirm Password")
    age = IntegerField("Age", validators=[DataRequired(), NumberRange(min=0)])
    weight = FloatField("Weight", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Sign Up")
    email = StringField("Email", validators=[DataRequired()])

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


# --------------------------------------------------------------------------------------------------------------------------------------
def current_user_id_db() -> str:
    user = Users.query.filter_by(username=current_user.username).first()
    return user.user_id
def find_users_weeks():
    user = Users.query.filter_by(username=current_user.username).first()
    if not user:
        print("User not found.")
        return None, None, None  # Handle case where user is not found

    user_id_db = user.user_id
    # Retrieve last mesocycle's data from my table
    last_meso_query = (db.session.query(Mesocycles)
                       .filter(Mesocycles.user_id == user_id_db)
                       .order_by(Mesocycles.mesocycle_id.desc())
                       .first())

    per_week_db = (
        db.session.query(Mesocycles.workouts_per_week)
        .filter(Mesocycles.user_id == user_id_db)
        .order_by(Mesocycles.mesocycle_id.desc())
        .first()
    )

    if per_week_db and per_week_db[0]:  # Check if per_week_db exists and contains a value
        last_workouts = (
            WorkoutPlan.query
            .filter(
                WorkoutPlan.user_id == user_id_db,
                WorkoutPlan.mesocycle_id == last_meso_query.mesocycle_id,
                WorkoutPlan.workout_name.isnot(None),
                WorkoutPlan.workout_name != "c"
            )
            .order_by(desc(WorkoutPlan.created_at))
            .limit(per_week_db[0])
            .all()
        )
        #print(f"Last workouts: {last_workouts}")

        try:
            last_workouts_id = (
                db.session.query(WorkoutPlan.workout_id)
                .filter(WorkoutPlan.workout_name != "c",
                        WorkoutPlan.user_id == user_id_db,
                         WorkoutPlan.mesocycle_id == last_meso_query.mesocycle_id,
                         WorkoutPlan.workout_name.isnot(None),)
                .order_by(WorkoutPlan.created_at.desc())
                .limit(per_week_db[0])
                .all()
            )
            

            workouts_id = [x[0] for x in last_workouts_id] if last_workouts_id else []
        except Exception as e:
            workouts_id = []
            db.session.rollback()

        workout_names_in_db = [workout.workout_name for workout in last_workouts]

        return per_week_db[0], workout_names_in_db, workouts_id

    return None, None, None
# Append exercises to jinja_exercises nested dict - use in jinja to display added exercises
def exercises_for_jinja(jinja_exercises, weekly, workouts_id):
    appendable_dict = {"exercise": None, "sets": None, "pauses": None}
    for x in range(weekly):
        # Access exercises for specific exercises
        exercise_details = (
            db.session.query(
                WorkoutExercises.exercise_id,
                WorkoutExercises.prescribed_sets,
                WorkoutExercises.rest_period,
            )
            .filter_by(workout_id=workouts_id[x])
            .all()
        )

        if exercise_details:
            for exes in exercise_details:
                # We are at 1. exercise (360, 2, 120)
                # Translate exe_id into Exe name

                specific_exercise_name = (
                    db.session.query(Exercise.exercise_name)
                    .filter_by(exercise_id=exes[0])
                    .first()
                )

                appendable_dict = {
                    "exercise": specific_exercise_name,
                    "sets": exes[1],
                    "pauses": exes[2],
                }
                # Append this to jinja_exercises
                jinja_exercises[x].append(appendable_dict)
# Default order in list
# Default dict for exercises: jinja_exercises
def default_order(weekly):
    jinja_exercises = {}
    default_order = []

    for x in range(weekly):
        default_order.append(1)
        jinja_exercises[x] = []

    return default_order, jinja_exercises
# Overwrite exercises, sets or rest period
def overwrite_exercise(submitted_data, weekly, workouts_id, jinja_exercises):
    for day in range(weekly):
        # Reset counters for each day
        count, count_sets, count_pauses = -1, -1, -1

        # Filter keys for the current day
        day_exercise_keys = sorted([k for k in submitted_data if k.startswith(f"exercise_{day}")])
        day_sets_keys = sorted([k for k in submitted_data if k.startswith(f"sets_{day}")])
        day_pauses_keys = sorted([k for k in submitted_data if k.startswith(f"pauses_{day}")])

        # Process exercises for the current day
        for key in day_exercise_keys:
            count += 1
            exe_name = submitted_data[key]

            # Get the new exercise ID
            exercise_id_query = (
                db.session.query(Exercise.exercise_id)
                .filter_by(exercise_name=exe_name)
                .first()
            )

            if exercise_id_query:
                current_exercise_id = exercise_id_query[0]

                # Get the previous exercise ID from jinja_exercises
                try:
                    previous_exercise = jinja_exercises[day][count]["exercise"][0]
                    previous_exercise_id_query = (
                        db.session.query(Exercise.exercise_id)
                        .filter_by(exercise_name=previous_exercise)
                        .first()
                    )

                    if previous_exercise_id_query:
                        # Update the exercise ID in WorkoutExercises
                        db.session.query(WorkoutExercises).filter_by(
                            workout_id=workouts_id[day],
                            exercise_id=previous_exercise_id_query[0],
                        ).update({"exercise_id": current_exercise_id})
                except IndexError as ie:
                    print(f"You are out of range {ie}")

        # Process sets for the current day
        count_sets = -1
        for key in day_sets_keys:
            count_sets += 1
            exe_sets = submitted_data[key]

            # Get the current exercise ID from jinja_exercises
            try:
                current_exercise_name = jinja_exercises[day][count_sets]["exercise"][0]
                current_exercise_id_query = (
                    db.session.query(Exercise.exercise_id)
                    .filter_by(exercise_name=current_exercise_name)
                    .first()
                )

                if current_exercise_id_query:
                    current_exercise_id = current_exercise_id_query[0]

                    # Update the prescribed sets in WorkoutExercises
                    db.session.query(WorkoutExercises).filter_by(
                        workout_id=workouts_id[day],
                        exercise_id=current_exercise_id,
                    ).update({"prescribed_sets": exe_sets})
            except IndexError as ie:
                print(f"You are out of range for sets {ie}")

        # Process pauses for the current day
        count_pauses = -1
        for key in day_pauses_keys:
            count_pauses += 1
            exe_pauses = submitted_data[key]

            # Get the current exercise ID from jinja_exercises
            try:
                current_exercise_name = jinja_exercises[day][count_pauses]["exercise"][0]
                current_exercise_id_query = (
                    db.session.query(Exercise.exercise_id)
                    .filter_by(exercise_name=current_exercise_name)
                    .first()
                )

                if current_exercise_id_query:
                    current_exercise_id = current_exercise_id_query[0]

                    # Update the rest period in WorkoutExercises
                    db.session.query(WorkoutExercises).filter_by(
                        workout_id=workouts_id[day],
                        exercise_id=current_exercise_id,
                    ).update({"rest_period": exe_pauses})
            except IndexError as ie:
                print(f"You are out of range for pauses {ie}")

        # Commit changes after processing each day
        db.session.commit()
def find_workout_name_from_user(submitted_data, weekly, workout_names) -> None:
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
def add_exercise(submitted_data, order, weekly, jinja_exercises, workouts_id):
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

                exercise_count = (
                    db.session.query(WorkoutExercises)
                    .filter_by(workout_id=workouts_id[day])
                    .count()
                )

                rest, sets = user_input_or_defualt()
                if exercise_count >= 1:

                    print(f"total exercises in this workout: {exercise_count + 1}")
                    # Add new exercise to database
                    new_exercise_order = exercise_count + 1
                    new_exercise_entry = {
                        "order_in_workout": new_exercise_order,  # Match with the unique input name
                        "exercise_id": exe_id.exercise_id,  # Match with the unique input name
                        "prescribed_sets": sets,
                        "rest_period": rest,
                        "workout_id": workouts_id[day],
                    }

                    new_exercise = WorkoutExercises(**new_exercise_entry)
                    db.session.add(new_exercise)
                    db.session.commit()

                elif exercise_count == 0:
                    new_exercise_order = exercise_count + 1
                    new_exercise_entry = {
                        "order_in_workout": new_exercise_order,  # Match with the unique input name
                        "exercise_id": exe_id.exercise_id,  # Match with the unique input name
                        "prescribed_sets": int(sets),
                        "rest_period": int(rest),
                        "workout_id": workouts_id[day],
                    }

                    new_exercise = WorkoutExercises(**new_exercise_entry)
                    db.session.add(new_exercise)
                    db.session.commit()

                    print("No exercise")

    return order
# Delete function
def delete_exercise(submitted_data, weekly, workouts_id):
    for day in range(weekly):
        delete_keys = [
            key for key in submitted_data.keys() if key.startswith(f"remove_{day}_")
        ]

        for key in delete_keys:
            parts = key.split("_")

            if len(parts) == 3:
                _, day_str, idx_str = parts
                idx = int(idx_str)
                delete_value = submitted_data.get(key)

                exercise = submitted_data.get(f"exercise_{day}_{idx}")

                specific_exercise_id = (
                    db.session.query(Exercise.exercise_id)
                    .filter_by(exercise_name=exercise)
                    .first()
                )

                if specific_exercise_id:
                    workout_id_found = (
                        db.session.query(WorkoutExercises.workout_exercise_id)
                        .filter_by(
                            workout_id=workouts_id[day],
                            exercise_id=specific_exercise_id[0],
                        )
                        .first()
                    )
                    # Remove the exercise
                    # DELTE FROM WorkoutExercises
                    # WHERE workout_exercise_id = workout_id_found.workout_exercise_id

                    remove_exe_from_db = (
                        db.session.query(WorkoutExercises)
                        .filter(
                            WorkoutExercises.workout_exercise_id
                            == workout_id_found.workout_exercise_id
                        )
                        .delete(synchronize_session=False)
                    )
                    db.session.commit()

            else:
                print(f"Unexpected key format: {key}")
# For tryining sessions mainly ---------------------------------------
def add_session_to_db(chosen_day_by_user, workouts_id):
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    # Map the chosen day to the actual workout_id
    workout_id_hopefully = workouts_id[chosen_day_by_user]
    
    print(f"day {chosen_day_by_user} and workouts_id {workouts_id}")
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
            user_id=user_id_db, workout_id=workout_id_hopefully, notes="Null",
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
def find_exercise_id_db(exercise):
    find_exercise_query = (
        db.session.query(Exercise.exercise_id)
        .filter(Exercise.exercise_name == exercise)
        .first()
    )

    if find_exercise_query:
        return find_exercise_query
    else:
        return None
def find_exercise_name_db(id):
    find_exercise_query = (
        db.session.query(Exercise.exercise_name)
        .filter(Exercise.exercise_id == id)
        .first()
    )

    if find_exercise_query:
        return find_exercise_query
    else:
        return None
def add_set_to_db(submitted_data, exercise, chosen_day) -> dict:
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    if exercise is not None:
        workout_id_from_db = (
            db.session.query(WorkoutPlan.workout_id)
            .filter(
                WorkoutPlan.user_id == user_id_db,
                WorkoutPlan.workout_name == chosen_day,
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )

        # Add set to database - exercise_entries
        # SELECT session_id FROM Sessions WHERE workout_id = my_workout_id ORDER BY session_id DESC
        if workout_id_from_db is not None:
            
            session_id_form_db = (
                db.session.query(Sessions.session_id)
                .filter(Sessions.workout_id == workout_id_from_db[0])
                .order_by(desc(Sessions.session_date)).first()
            )

            if not session_id_form_db:
                session_id_form_db = (
                db.session.query(Sessions.session_id)
                .filter(Sessions.workout_id == chosen_day)
                .order_by(desc(Sessions.session_date)).first()
            )

            exe_id = find_exercise_id_db(exercise)

            try:
                # Find total sets in ExerciseEntries
                sets_yet = (
                    db.session.query(ExerciseEntries.set_number)
                    .filter(
                        ExerciseEntries.session_id == session_id_form_db[0],
                        ExerciseEntries.exercise_id == exe_id[0],
                    )
                    .count()
                )
            except TypeError:
                db.session.rollback()
                print("Bro, there is no session yet, but I will set 0 for you")
                sets_yet = 0
                sets_yet += 1

            # Check if user didn't refresh website / if so it would add another set
            # So check if there is not the

            # Save exdrcise entry into database
            try:
                exercise_entry_add = ExerciseEntries(
                    session_id=session_id_form_db[0],
                    exercise_id=exe_id[0],
                    set_number=sets_yet,
                    reps=int(submitted_data.get("reps", 0)),
                    weight=float(submitted_data.get("kg", 0.0)),
                    rpe=int(submitted_data.get("rpe", 0)),
                    notes=submitted_data.get("notes", ""),
                )
                db.session.add(exercise_entry_add)
                db.session.commit()
            except Exception as e:
                print(f"Exception line {inspect.currentframe().f_lineno}: {e}")
                db.session.rollback()
# Sets for jinja
def jinja_sets_function(chosen_day, chosen_exercise):
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    if chosen_exercise:
        exercise_id = find_exercise_id_db(chosen_exercise)[0]
    else:
        return None
    
    if not exercise_id:
        print(f"Exercise '{chosen_exercise}' not found.")
        return None

    workout_id_from_db = (
    db.session.query(WorkoutPlan.workout_id)
    .filter(
        WorkoutPlan.workout_name == chosen_day,
        WorkoutPlan.user_id == user_id_db
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
            print("Desired session not found.")
            return None
    else:
        print("Workout ID not found.")
        return None
def delete_set(submitted_data):
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
def exercise_preview(workout_id, workout_key, chosen_exercise, chosen_day_by_user, workouts_id):
    user_id_db = current_user_id_db()
    preview = {"exercise": None,"sets": None, "reps": None, "weight": None, "rpe": None, "notes": None, "done": None}
    preview_data = []

    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)

    if workout_id and workout_key is not None:
        select_all_exercises = (
            db.session.query(WorkoutExercises)
            .filter(WorkoutExercises.workout_id == workout_id[workout_key])
            .all()
        )
        
        exe_list = []
        if select_all_exercises:
            # Populate dict with exercises
            for exers in select_all_exercises:
                exercise_name = find_exercise_name_db(exers.exercise_id)[0]
    
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
                    print("You have nothing chosen so far")
                    db.session.rollback()
                    today_session = None

                done = None

                if latest_entry and today_session:
                    if latest_entry.session_id != today_session:
                        """ print(latest_entry.session_id, ' : ', today_session)
                        print("We are green bro") """
                        pass
                    else:
                        """ print(latest_entry.session_id, ' : ', today_session)
                        print("We are not green bro") """
                        done = "yes"
                else:
                    pass
                
                # Populate the preview entry with data from the latest_entry or default values
                preview_entry = {
                    "exercise": exercise_name,
                    "sets": exers.prescribed_sets,
                    "reps": latest_entry.reps if latest_entry and latest_entry.reps is not None else 0,
                    "weight": latest_entry.weight if latest_entry and latest_entry.weight is not None else 0,
                    "rpe": latest_entry.rpe if latest_entry and latest_entry.rpe is not None else 0,
                    "notes": latest_entry.notes if latest_entry and latest_entry.notes else "",
                    "done" : done
                }
                
                preview_data.append(preview_entry)

            return preview_data

        else:

            return {None : None}           
# Modify sets which user already saved
def modify_set(submitted_data):
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
def sets_to_do(chosen_exercise, chosen_day):
    current_user_id = current_user_id_db()
    # Exercise id
    try:
        exercise_id = find_exercise_id_db(chosen_exercise)[0]
    except Exception as e:
        exercise_id = None
        print(f"exercise_id is None probably: {e}")

    if exercise_id:
        workout_id = db.session.query(WorkoutPlan.workout_id).filter(
            WorkoutPlan.user_id == current_user_id,
            WorkoutPlan.workout_name == chosen_day
        ).order_by(desc(WorkoutPlan.created_at)).first()
        
        if workout_id:
            # Search workout_exercise_id for prescribed sets
            specific_exercise = db.session.query(WorkoutExercises).filter(
                WorkoutExercises.workout_id == workout_id[0],
                WorkoutExercises.exercise_id == exercise_id
            ).first()

            if specific_exercise:
                return specific_exercise.prescribed_sets
            else:
                return None
def current_exercise_info(chosen_exercise, chosen_day):
    current_user_id = current_user_id_db()
    # Exercise id
    try:
        exercise_id = find_exercise_id_db(chosen_exercise)[0]
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
            .order_by(desc(ExerciseEntries.session_id), desc(ExerciseEntries.weight), desc(ExerciseEntries.reps))
            .first()
        )

        # Get the heaviest weight for the exercise in the last session
        # Ensure previous_exercise_entry exists
        if previous_exercise_entry:
            # Get the heaviest weight entry for that session and exercise
            heaviest_weight_entry = (
                db.session.query(ExerciseEntries)
                .filter(
                    ExerciseEntries.exercise_id == previous_exercise_entry.exercise_id,
                    ExerciseEntries.session_id == previous_exercise_entry.session_id
                )
                .order_by(desc(ExerciseEntries.entry_id), desc(ExerciseEntries.weight))
                .first()
            )
        else:
            heaviest_weight_entry = None

        if heaviest_weight_entry:
            return heaviest_weight_entry
        else:
            return None
def show_tables_to_user(current_user) -> dict:
    current_user_id = current_user_id_db()

    # Find all workouts and exercises for this user. Return dict
    mesocycle_info = {}
    workout_ids = []

    user_mesocycles = db.session.query(Mesocycles).filter(
        Mesocycles.user_id == current_user
    ).all()

    for i, x in enumerate(user_mesocycles):
        # Find workout_id and add it to dict
        workout_id = db.session.query(WorkoutPlan.workout_id).filter(
            WorkoutPlan.mesocycle_id ==  x.mesocycle_id
        ).all()
        
        if workout_id:
            for work_id in workout_id:
                workout_ids.append(work_id[0])


            # {i:{meso_id: meso_name, duration: weeks, per_week: times}}
            mesocycle_info[i] = {x.name: x.mesocycle_id, "duration": x.mesocycle_duration_weeks, "per_week": x.workouts_per_week, "workout_ids":workout_ids}
            
            workout_ids = []

    return mesocycle_info 
def tables_informations(chosen_mesocycle: str, mesocycle_info: dict) -> dict:
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
            duration = value.get('duration')
            per_week = value.get('per_week')
            workout_ids = value.get('workout_ids')
            break          

    if workout_ids:
        for wid in workout_ids:
            workout_name_db = db.session.query(WorkoutPlan.workout_name).filter(
                WorkoutPlan.workout_id == wid,
            ).first()  
            if workout_name_db:
                w_name_to_dict = workout_name_db[0]
                workout_exercises = db.session.query(WorkoutExercises).filter(
                    WorkoutExercises.workout_id == wid,
                ).all()
                
                # Initialize a dictionary for this workout
                exercise_dict = {}
                if workout_exercises:
                    for wex in workout_exercises:
                        try:
                            exercise_name = find_exercise_name_db(wex.exercise_id)[0]
                            exercise_details = {
                                'rest': wex.rest_period,
                                'sets': wex.prescribed_sets
                            }
                            # Add exercise details to the dictionary
                            exercise_dict[exercise_name] = exercise_details
                        except Exception as e:
                            print(f"Could not find your exercise name: {e}")

                # Add the constructed exercise_dict to the main dictionary under the workout name
                workouts_from_db[w_name_to_dict] = exercise_dict

    return workouts_from_db
def workout_day_information(chosen_mesocycle: str, mesocycle_info: dict) -> dict:
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
            duration = value.get('duration')
            per_week = value.get('per_week')
            workout_ids = value.get('workout_ids')
            break     
    
    
    if workout_ids:
        for wid in workout_ids:
            workouts_list = []
            workout_name_db = db.session.query(WorkoutPlan.workout_name).filter(
                WorkoutPlan.workout_id == wid,
            ).first()  
            if workout_name_db:
                w_name_to_dict = workout_name_db[0]
                workout_exercises = db.session.query(WorkoutExercises).filter(
                    WorkoutExercises.workout_id == wid,
                ).all()       
            
                #print(f"what do we have here{workout_name_db[0]} - {wid}")

                for exrs in workout_exercises:
                    exercise_name_for_list = find_exercise_name_db(exrs.exercise_id)[0]
                    workouts_list.append(exercise_name_for_list)
                workouts_from_db[w_name_to_dict] = workouts_list
    
    return workouts_from_db
# Information about progress prepared for jinja2
def exercise_progress_data(workout_info, chosen_day, mesocycle_name):
    current_user_id = current_user_id_db()
    mesocycle_id = db.session.query(Mesocycles.mesocycle_id).filter(
        Mesocycles.name == mesocycle_name,
        Mesocycles.user_id == current_user_id
    ).first()[0]

    result_set = {}

    if chosen_day and mesocycle_id:
        for key, value in workout_info.items():
            if chosen_day in key:
                # I need to get first exercise user made in his mesocycle and last one -> date, reps weight, rpe
                workout_id = db.session.query(WorkoutPlan.workout_id).filter(
                    WorkoutPlan.user_id == current_user_id,
                    WorkoutPlan.workout_name == key,
                    WorkoutPlan.mesocycle_id == mesocycle_id
                ).order_by(desc(WorkoutPlan.created_at)).first()[0]

                # First session exercise_entry
                if workout_id:
                    
                    try:
                        first_session = db.session.query(Sessions.session_id).filter(
                            Sessions.user_id == current_user_id,
                            Sessions.workout_id == workout_id
                        ).first()
                    except:
                        first_session = None
                        print("No data yet bro")
                    all_sessions = db.session.query(Sessions).filter(
                        Sessions.user_id == current_user_id,
                        Sessions.workout_id == workout_id
                    ).all()
                    
                    exercises_in_workout = db.session.query(WorkoutExercises).filter(
                                WorkoutExercises.workout_id == workout_id
                            ).all()
                    
                    if exercises_in_workout:
                        for exrs in exercises_in_workout:
                            exercise_name = find_exercise_name_db(exrs.exercise_id)[0]
                            small_data_list = []

                            for sess in all_sessions:
                                find_exe = db.session.query(ExerciseEntries).filter(
                                    ExerciseEntries.session_id == sess.session_id,
                                    ExerciseEntries.exercise_id == exrs.exercise_id
                                ).all()

                                for som in find_exe:
                                    # Create a new small_data_set dictionary for each entry
                                    small_data_set = {
                                        "date": f"{sess.session_date.day}.{sess.session_date.month}.{sess.session_date.year}",
                                        "reps": som.reps or 0,
                                        "weight": som.weight or 0,
                                        "rpe": som.rpe or 0,
                                        "notes": som.notes or ""
                                    }
                                    small_data_list.append(small_data_set)

                            # Add the list of exercise data to the result_set
                            result_set[exercise_name] = small_data_list

                        return result_set
    else: 
        return {None:None}
# AJAX for exercises preview when creating workout
def fetch_exercise_suggestions(search_term):
    exercises = Exercise.query.filter(
        Exercise.exercise_name.ilike(f"%{search_term}%")
    ).all()
    return [exercise.exercise_name for exercise in exercises]
def get_today_intuitive_traing():
    current_user_id = current_user_id_db()
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)

    today_check_query = (
            db.session.query(WorkoutPlan)
            .filter(
                and_(
                    WorkoutPlan.user_id == current_user_id,
                    WorkoutPlan.created_at >= today,
                    WorkoutPlan.created_at < tomorrow,
                    WorkoutPlan.workout_name.like("%_intuitive")
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
def create_custom_workout_exercise(exercise_name):
    user_id_db = current_user_id_db()
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)
    # Find exercise_id for exercise user have inputed
    exe_id = (
        db.session.query(Exercise).filter_by(exercise_name=exercise_name).first()
    )

    # Find workout id and order in workout
    workout_id_query =  (
            db.session.query(WorkoutPlan)
            .filter(
                and_(
                    WorkoutPlan.user_id == user_id_db,
                    WorkoutPlan.created_at >= today,
                    WorkoutPlan.created_at < tomorrow,
                    WorkoutPlan.workout_name == "c"
                )
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )

    if workout_id_query:
        # Check if exercise is in WorkoutExercises table
        exercise_already_in_table = (db.session.query(WorkoutExercises)
                                    .filter(WorkoutExercises.workout_id == workout_id_query.workout_id,
                                            WorkoutExercises.exercise_id == exe_id.exercise_id)
                                    .first())
        if exercise_already_in_table is None:
                order = (db.session.query(WorkoutExercises)
                        .filter(WorkoutExercises.workout_id == workout_id_query.workout_id)
                        .count())
                if order == 0:
                    order = 1

                new_workout_exercise = WorkoutExercises(workout_id=workout_id_query.workout_id, exercise_id=exe_id.exercise_id, order_in_workout=order, prescribed_sets=2, rest_period=120)

                try:
                    db.session.add(new_workout_exercise)
                    db.session.commit()

                    added_exercise = (db.session.query(WorkoutExercises)
                                        .filter(WorkoutExercises.workout_id == workout_id_query.workout_id,
                                                WorkoutExercises.exercise_id == exe_id.exercise_id)
                                        .first())
                    
                    return True
                except Exception as e:
                    db.session.rollback()
                    return False         
# Function to add exercise to database for intuitive training
def add_intuitive_exercise(exercise):
    user_id_db = current_user_id_db()

    # Check if there is exercise in database
    exercise_in_db = (db.session.query(Exercise)
                      .filter(Exercise.exercise_name == exercise)
                      .first())


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
                    WorkoutPlan.workout_name.like("%_intuitive")
                )
            )
            .order_by(desc(WorkoutPlan.created_at))
            .first()
        )

        if workout_id_query:
            # Check if exercise is in WorkoutExercises table
            exercise_already_in_table = (db.session.query(WorkoutExercises)
                                        .filter(WorkoutExercises.workout_id == workout_id_query.workout_id,
                                                WorkoutExercises.exercise_id == exercise_in_db.exercise_id)
                                        .first())

            if exercise_already_in_table is None:
                order = (db.session.query(WorkoutExercises)
                        .filter(WorkoutExercises.workout_id == workout_id_query.workout_id)
                        .count())
                if order == 0:
                    order = 1

                new_workout_exercise = WorkoutExercises(workout_id=workout_id_query.workout_id, exercise_id=exercise_in_db.exercise_id, order_in_workout=order, prescribed_sets=2, rest_period=90)

                try:
                    db.session.add(new_workout_exercise)
                    db.session.commit()

                    added_exercise = (db.session.query(WorkoutExercises)
                                        .filter(WorkoutExercises.workout_id == workout_id_query.workout_id,
                                                WorkoutExercises.exercise_id == exercise_in_db.exercise_id)
                                        .first())
                    
                    print(find_exercise_name_db(added_exercise.exercise_id)[0])
                    return find_exercise_name_db(added_exercise.exercise_id)[0]
                except Exception as e:
                    db.session.rollback()
                    print(f"Sorry, but there was some problem adding you exercise into database: {e}")
                    return None
            else:
                print("You already have this exercise in your workout plan so don't be stupid")
                return None
        else:
            return None
    else:
        return None
# Custom workout - check if current day exists
def check_c_session():
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
def create_custom_session():
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)

    # Create custom session - 'c' for simple search in DB
    new_session_query = Sessions(
            user_id=user_id_db, workout_id="c", notes="Null",
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
def create_custom_workout_plan():
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

    today_workout = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id_db,
        WorkoutPlan.created_at >= today,
        WorkoutPlan.created_at < tomorrow,
        WorkoutPlan.workout_name == "c",
    ).first()
    
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
def load_custom_exercises_for_day():
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)

    result = []

    today_workout = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id_db,
        WorkoutPlan.created_at >= today,
        WorkoutPlan.created_at < tomorrow,
        WorkoutPlan.workout_name == "c",
    ).first()

    if today_workout:
        find_saved_exercises_query = db.session.query(WorkoutExercises).filter(
            WorkoutExercises.workout_id == today_workout.workout_id
        ).all()

        for x in find_saved_exercises_query:
            result.append(find_exercise_name_db(x.exercise_id)[0])

    return result
# Load data for each user's exercise - first and last entry 
def exercises_progress():
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id
    all_sessions = []
    first_exercise = []
    last_exercise = []
    temp = []
    temp_last = []
    
    # Select * sessions for current user
    sessions_query = db.session.query(Sessions).filter(
        Sessions.user_id == user_id_db
    ).all()
    
    for sess in sessions_query:
        all_sessions.append(sess.session_id)

    # Select all exercises with corresponding sesions
    first_exercise_query = db.session.query(ExerciseEntries).filter(
        ExerciseEntries.session_id.in_(all_sessions)
    ).all()

    last_exercise_query = db.session.query(ExerciseEntries).filter(
        ExerciseEntries.session_id.in_(all_sessions)
    ).order_by(ExerciseEntries.session_id.desc()).all()


    # Filter out first time exercises
    for exercise in first_exercise_query:
        if exercise.exercise_id not in temp:
            first_exercise.append(exercise.exercise_id)
        temp.append(exercise.exercise_id)

    # Filter out last time exercises
    for exercise in last_exercise_query:
        if exercise.exercise_id not in temp_last:
            last_exercise.append(exercise.exercise_id)
        temp_last.append(exercise.exercise_id)

    return last_exercise
# Load last custom workout day for jinja_sets_function
def last_custom_day():
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    # SELECT last workout FROM  WorkoutPlan
    last_c_work_query = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id_db
    ).order_by(WorkoutPlan.created_at.desc()).first()

    return last_c_work_query

# --------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(
            form.password.data, method="pbkdf2:sha256"
        )
        new_users = Users(
            username=form.username.data,
            password=hashed_password,
            age=form.age.data,
            email=form.email.data,
            weight=form.weight.data,
        )
        db.session.add(new_users)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        #print(f"test: {form.password.data}")
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("index_page"))
        else:
            flash(
                "Login unsuccessful. Please check your username and password.", "danger"
            )
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index_page"))

@app.route("/home")
def home():
    return redirect(url_for("index_page"))

@app.route("/")
def index_page():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")

    if current_user.is_authenticated:
        username = current_user.username
    else:
        username = None
    return render_template("index.html", user=username, year=YEAR)

# Workout Plan ---------------------------------------------------------
@app.route("/workout_plan")
@login_required
def workout_plan():
    return redirect(url_for("workout_plan_page"))

@app.route("/workout_plan_page", methods=["GET", "POST"])
@login_required
def workout_plan_page():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")
    submitted_data = request.form.to_dict()
    current_user_id = current_user_id_db()
    # Load amount of mesocycles
    all_users_mesocycles_query = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user_id
    )

    try:
        if all_users_mesocycles_query:
            print("There are some workout already in your mesocycle")
            dropdown_menu_info = show_tables_to_user(current_user_id)

            try:
                chosen_mesocycle = submitted_data["mesocycle"]
                session["chosen_mesocycle"] = chosen_mesocycle
            except KeyError as ke:
                chosen_mesocycle = None
            
            table_population = tables_informations(chosen_mesocycle, dropdown_menu_info)
            print(table_population)
            

    except TypeError:
        return render_template("table_layout.html", year=YEAR)


    return render_template(
        "workout.html",
        year=YEAR,
        dropdown=dropdown_menu_info,
        chosen_mesocycle=chosen_mesocycle,
        table_population=table_population
    )

# ----------------------------------------------------------------------
@app.route("/table_layout", methods=["GET", "POST"])
@login_required
def table_layout():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")
    user_id = current_user_id_db()
    username = current_user.username

    if request.method == "POST":
        meso_name = request.form.get("meso_name")
        meso_duration = request.form.get("mesocycle")
        workouts_per_week = request.form.get("per_week")

        try:
            mesocycles_db = Mesocycles(
                name=meso_name,
                user_id=user_id,
                mesocycle_duration_weeks=meso_duration,
                workouts_per_week=workouts_per_week,
            )

            db.session.add(mesocycles_db)
            db.session.commit()

            # Find this mesocycle in db
            mesocycle_id = db.session.query(Mesocycles.mesocycle_id).filter(
                Mesocycles.user_id == user_id
            ).order_by(desc(Mesocycles.mesocycle_id)).first()

            if mesocycle_id:
                # Create rows in WorkoutPlan / workouts based on workout_per_week ... Workout name default to number of weeks
                # INSERT INTO workouts (user_id, workout_name) VALUES (CurrentUser.username, meso_name)
                for i in range(int(workouts_per_week)):
                    user = Users.query.filter_by(username=current_user.username).first()
                    user_id_db = user.user_id

                    # For OOP this have to go away into reausable function
                    table = WorkoutPlan(
                        workout_name=i,
                        user_id=user_id_db,
                        mesocycle_id=mesocycle_id[0]
                    )
                    db.session.add(table)
                db.session.commit()
            return redirect(url_for("create_workout"))
        except:
            db.session.rollback()
            return redirect(url_for("home"))
            
    return render_template("table_layout.html", year=YEAR)

# Here is created mesocycle workout
@app.route("/create_workout", methods=["GET", "POST"])
@login_required
def create_workout():
    weekly, workout_names, workouts_id = find_users_weeks()

    # Default order
    order, jinja_exercises = default_order(weekly)

    exercises_for_jinja(jinja_exercises, weekly, workouts_id)

    if request.method == "GET":
        # Handle AJAX request for exercise search
        search_term = request.args.get("query")

        if search_term:
            exercise_names = fetch_exercise_suggestions(search_term)
            return jsonify(exercise_names)

    elif request.method == "POST":
        # Process form submission and save the workout data
        submitted_data = request.form.to_dict()

        # Name of workout is default set 1-x and user can change it
        workout_names = find_workout_name_from_user(submitted_data, weekly, workout_names)

        # Save new exercise into database - return order number
        exercises_dict = add_exercise(submitted_data, order, weekly, jinja_exercises, workouts_id)

        # Call function to delete exercise from workout
        delete_exercise(submitted_data, weekly, workouts_id)

        # Call function to overwrite exercise
        overwrite_exercise(submitted_data, weekly, workouts_id, jinja_exercises)

        # Use the PRG pattern: Redirect to prevent resubmission
        return redirect(url_for("create_workout"))

    return render_template(
        "create_workout.html",
        week=weekly,
        w_names=workout_names,
        exe_order=order,
        user_exe=jinja_exercises,
    )

# Training session ---------------------------------------------------------
@app.route("/training_session_redirect", methods=["GET"])
def training_session_redirect():
    return redirect(url_for("training_session"))

@app.route("/training_session", methods=["GET", "POST"])
@login_required
def training_session():
    NOW = datetime.now()
    DATE = NOW.strftime("%d%m%Y")
    YEAR = NOW.strftime("%Y")

    # Function to acces workout day / data from database
    weekly, workout_names, workout_id = find_users_weeks()

    # If user did not 'create training and wants to do workouts... not on my watch
    if weekly is None:
        return redirect(url_for("home"))

    # NOTE: Order will be used later for strict oder of exercises during session and option to change it
    order, jinja_exercises = default_order(weekly)
    
    exercises_for_jinja(jinja_exercises, weekly, workout_id)

    workouts_id_name = {}
    # Make dick like this: 1: "Upper Body"
    for i in range(weekly):
        workouts_id_name[i] = workout_names[i]

    chosen_day = session.get("chosen_day")
    print(f"chosen day : {chosen_day}")
    chosen_exercise = session.get("chosen_exercise")

    # Create list of exercises -> for jinja purposes
    workout_key = next((k for k, v in workouts_id_name.items() if v == chosen_day), 0)

    exercises_from_user: dict = jinja_exercises[workout_key]
    exercises_in_workout: list = [x["exercise"][0] for x in exercises_from_user]

    load_workout_day = request.args.get("training_day")

    if request.method == "GET":

        # If the user made a selection, update `chosen_day` and store in session
        if load_workout_day is not None:
            # Clear if the selection is blank (like a placeholder)
            if load_workout_day == "":
                session.pop("chosen_day", None)  # Remove chosen day from session
                chosen_day = None
            else:
                session["chosen_day"] = load_workout_day
                chosen_day = load_workout_day  # Update variable with the new choice
                # If day is changed, pop session
                session.pop("chosen_exercise", None)
                return redirect(url_for("training_session"))

        load_chosen_exercise = request.args.get("chosen_exercise")

        if load_chosen_exercise is not None:
            if load_chosen_exercise == "":
                session.pop("chosen_exercise", None)
                load_chosen_exercise = None
            else:
                session["chosen_exercise"] = load_chosen_exercise
                chosen_exercise = load_chosen_exercise

    elif request.method == "POST":
        add_session_to_db(workout_key, workout_id)

        submitted_data = request.form.to_dict()

        add_set_to_db(submitted_data, chosen_exercise, chosen_day)

        delete_set(submitted_data)

        # Get access to sets / exercises user want to change
        modify_set(submitted_data)

    sets_for_jinja = jinja_sets_function(chosen_day, chosen_exercise)

    # Reset placeholders to zero after the first set is saved
    if sets_for_jinja:
        exercise_placeholders = {'weight': 0, 'reps': 0, 'rpe': 0, 'notes': '...'}
    else:
        exercise_placeholders = current_exercise_info(chosen_exercise, chosen_day)

    preview = exercise_preview(workout_id, workout_key, chosen_exercise, workout_key, workout_id)
    sets_to_do_jinja = sets_to_do(chosen_exercise, chosen_day)
    
    return render_template(
        "training_session.html",
        today=DATE,
        year=YEAR,
        w_names=workouts_id_name,
        weeks=weekly,
        chosen_day=chosen_day,
        exercises_to_display=exercises_in_workout,
        chosen_exercise=chosen_exercise,
        sets_for_jinja=sets_for_jinja,
        preview=preview,
        placeholders= exercise_placeholders
    )

# --------------------------------------------------------------------------
@login_required
@app.route("/execute_workout_plan_exercises")
def execute_workout_plan_exercises():
    return render_template("<h1>Just test if process will pass<h1>")
# --------------------------------------------------------------------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    action = request.form.get('action')

    if action == 'change_mesocycle':
        # Handle changing the mesocycle
        return redirect(url_for("create_workout"))
    elif action == 'show_progress':
        # Handle showing progress
        return redirect(url_for("progress"))
    elif action == 'statistics':
        # Handle statistics
        return redirect(url_for("statistics"))
    elif action == 'change_password':
        # Handle changing password
        return "For now you need to contact admit to change your password. <br>This function will be added in the future.</br>" 

    return render_template(
        "profile.html",
    )

# --------------------------------------------------------------------------
@login_required
@app.route("/progress", methods=["GET", "POST"])
def progress():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")
    DATE = NOW.strftime("%d%m%Y")
    exercise_progress = session.get("exercise_progress")
    session.pop("chosen_day", None) 

    current_user_id = current_user_id_db()
    # Function to access workout day / data from database
    weekly, workout_names, workout_id = find_users_weeks()

    # Load amount of mesocycles
    all_users_mesocycles_query = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user_id
    )

    # Initialize variables
    chosen_mesocycle = session.get("chosen_mesocycle")
    chosen_day = session.get("chosen_day")
    chosen_exercise = session.get("chosen_exercise")
    dropdown_menu_info = {}
    workout_day_info = {}

    if all_users_mesocycles_query:
        dropdown_menu_info = show_tables_to_user(current_user_id)

        if request.method == "POST":
            # Handle mesocycle selection
            submitted_data = request.form.to_dict()
            chosen_mesocycle = submitted_data.get("mesocycle")
            training_day = submitted_data.get("training_day")

            if chosen_mesocycle:
                session["chosen_mesocycle"] = chosen_mesocycle
                session["training_day"] = training_day
            else:
                # If no mesocycle selected, remove from session
                session.pop("chosen_mesocycle", None)
                session.pop("training_day", None)
                chosen_mesocycle = None

        # Ensure `chosen_mesocycle` is set before generating `workout_day_info`
        if chosen_mesocycle:
            workout_day_info = workout_day_information(chosen_mesocycle, dropdown_menu_info)
        else:
            workout_day_info = {}
    # If no workout plan exists redirect to workout creation        
    else:
        return render_template("table_layout.html", year=YEAR)

    if weekly is None:
        return redirect(url_for("home"))

    order, jinja_exercises = default_order(weekly)
    exercises_for_jinja(jinja_exercises, weekly, workout_id)

    workouts_id_name = {}
    # Make dict like this: {1: "Upper Body"}
    for i in range(weekly):
        workouts_id_name[i] = workout_names[i]

    # Create list of exercises -> for Jinja purposes
    workout_key = next((k for k, v in workouts_id_name.items() if v == chosen_day), 0)
    exercises_from_user = jinja_exercises.get(workout_key, [])
    exercises_in_workout = [x["exercise"][0] for x in exercises_from_user]

    # Handle GET parameters
    if request.method == "GET":
        load_workout_day = request.args.get("training_day")
        if load_workout_day is not None:
            if load_workout_day == "":
                session.pop("chosen_day", None)
                chosen_day = None
            else:
                session["chosen_day"] = load_workout_day
                chosen_day = load_workout_day
                # If day is changed, pop session
                session.pop("chosen_exercise", None)
                chosen_exercise = None
                return redirect(url_for("progress"))

        load_chosen_exercise = request.args.get("chosen_exercise")
        if load_chosen_exercise is not None:
            if load_chosen_exercise == "":
                session.pop("chosen_exercise", None)
                chosen_exercise = None
            else:
                session["chosen_exercise"] = load_chosen_exercise
                chosen_exercise = load_chosen_exercise
        
        if workout_day_info:
            exercise_progress = exercise_progress_data(workout_day_info, chosen_day, chosen_mesocycle)
    
    return render_template(
    "progress.html",
    today=DATE,
    year=YEAR,
    w_names=workouts_id_name,
    chosen_day=chosen_day,
    dropdown=dropdown_menu_info,
    chosen_mesocycle=chosen_mesocycle,
    workouts_info=workout_day_info,
    progress= exercise_progress,
)

@login_required
@app.route("/statistics", methods=["GET", "POST"])
def statistics():
    data = exercises_progress()
    print(data)
    return render_template("statistics.html")


@login_required
@app.route("/intuitive_training", methods=["GET", "POST"])
def intuitive_training():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")
    DATE = NOW.strftime("%d%m%Y")
    
    selected_exercise = None

    sets_for_jinja = None

    # If new exercise, then pop cookie for chosen exe and vice versa 
    new_exercise = session.get("new_exercise", None)
    chosen_exercise_dropdown_i = session.get("chosen_exercise_by_user", None)

    # Provide to jinja as result set to know what is now exercised
    if new_exercise: 
        selected_exercise = new_exercise
    elif chosen_exercise_dropdown_i:
        selected_exercise = chosen_exercise_dropdown_i

    # Read data for current exercise 
    placeholders = None
    today_session = check_c_session() # Return true / false
    session.permanent = True  # Mark session as permanent (uses configured timeout - 24 hours in my case)
    saved_exercises = load_custom_exercises_for_day()

    if request.method == "GET":
        # Check existance of the today's custom workout 
        user_confirm = request.args.get("confirm_freestyle")

        if user_confirm:
            # Create new session for today
            try_to_create_custom_w_plan = create_custom_workout_plan()
            if try_to_create_custom_w_plan:
                create_custom_session()
                return redirect(url_for('intuitive_training'))
        else:
            print('No confirmation yet')
            
        # Check if there are already some exercies in workout - In case website / webbrowser would crash and we had no POST after openin :)
        search_term = request.args.get("query")
        if search_term:
            exercise_names = fetch_exercise_suggestions(search_term)
            return jsonify(exercise_names)
        
    else:  # POST
        submitted_data = request.form.to_dict()
        action = submitted_data.get("action")

        if action == "choose_exercise":
            chosen_exercise = submitted_data.get("chosen_exercise")
            if chosen_exercise:
                session["chosen_exercise_by_user"] = chosen_exercise
                session.pop("new_exercise", None)
                return redirect(url_for("intuitive_training"))

        elif action == "add_exercise_name":
            # Same as choose_exercise this will aslo set new exercise as
            # currently exercised
            new_exercise = submitted_data.get("exercise")

            if new_exercise:
               create_custom_workout_exercise(new_exercise)
               session["new_exercise"] = new_exercise
               session.pop("chosen_exercise_by_user", None)
               return redirect(url_for("intuitive_training"))
            else:
                pass
            
        if submitted_data.get("reps"):
            day_for_function = "c"
            add_set_to_db(submitted_data, selected_exercise, day_for_function)
            print('reps_to_save are provided correctly')
    
    # Check for last sets
    last_day = last_custom_day()
    if chosen_exercise_dropdown_i:
        sets_for_jinja = jinja_sets_function("c", chosen_exercise_dropdown_i)
        print(f"Sets for jinja: {sets_for_jinja}")

    if not sets_for_jinja:
        sets_for_jinja = None

    return render_template(
        "intuitive_training.html",
        today=DATE,
        year=YEAR,
        today_session = today_session,
        saved_exercises = saved_exercises,
        selected_exercise = selected_exercise,
        placeholders = placeholders,
        sets_for_jinja = sets_for_jinja
    )

@app.errorhandler(404)
def page_not_found(e):
    # I need to put this date variables into function, too many repetiotions
    NOW = datetime.now()
    DATE = NOW.strftime("%d%m%Y")
    YEAR = NOW.strftime("%Y")

    return render_template(
        '404.html',
        today=DATE,
        year=YEAR,
    ), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False) # Delete this before pushing
