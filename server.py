import re
import os
from datetime import datetime

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
    inspect,
    text,
    select,
    desc,
    
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import FloatField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange

from sqlalchemy import func

#from workout_management import WorkoutManagement as wm

#training_session_data = wm.find_users_weeks()

NOW = datetime.now()
DATE = NOW.strftime("%d%m%Y")
YEAR = NOW.strftime("%Y")

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
    f"sqlite:///{os.path.join(basedir, "instance/workout.db")}"
)
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///workout.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

    def __init__(
        self,
        user_id,
        workout_name,
    ):
        self.user_id = user_id
        self.workout_name = workout_name
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
        user_id_db = user.user_id
        # Retrieve last mesocycle's data from my table
        per_week_db = (
            db.session.query(Mesocycles.workouts_per_week)
            .filter(Mesocycles.user_id == user_id_db)
            .order_by(Mesocycles.mesocycle_id.desc())
            .first()
        )

        last_workouts = (
            WorkoutPlan.query.filter_by(user_id=user_id_db)
            .order_by(desc(WorkoutPlan.created_at))
            .limit(per_week_db[0])
            .all()
        )

        try:
            last_workouts_id = (
                db.session.query(WorkoutPlan.workout_id)
                .filter(WorkoutPlan.user_id == user_id_db)
                .order_by(WorkoutPlan.created_at.desc())
                .limit(per_week_db[0])
                .all()
            )

            workouts_id = [x[0] for x in last_workouts_id] if last_workouts_id else []
        except Exception as e:
            print(f"Probably no workout created yet {e}")
            workouts_id = None

        workout_names_in_db = [workout.workout_name for workout in last_workouts]

        return per_week_db[0], workout_names_in_db, workouts_id


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
# Default disct for exercises: jinja_exercises
def default_order(weekly):
    jinja_exercises = {}
    default_order = []

    for x in range(weekly):
        default_order.append(1)
        jinja_exercises[x] = []

    return default_order, jinja_exercises

# Overwrite exercises, sets or rest period
def overwrite_exercise(submitted_data, weekly, workouts_id, jinja_exercises):
    count, count_sets, count_pauses = -1, -1, -1

    for day in range(weekly):
        user_exe = submitted_data.get(f"workout_name_{day}", "")

        for i, x in enumerate(submitted_data):
            # Catch exercise renaming
            if x.startswith(f"exercise_{day}"):
                count += 1

                exe_name = submitted_data[x]
                # print(f"day {day}: {exe_name}")

                exercise_id_query = (
                    db.session.query(Exercise.exercise_id)
                    .filter_by(exercise_name=exe_name)
                    .first()
                )

                if exercise_id_query:
                    current_exercise_id = exercise_id_query[0]
                    
                    current_workout_exercise_id = (
                        db.session.query(WorkoutExercises.workout_exercise_id)
                        .filter_by(
                            workout_id=workouts_id[day],
                            exercise_id=current_exercise_id,
                        )
                        .first()
                    )

                    if not current_workout_exercise_id:
                        try:
                            previous_exercise = jinja_exercises[day][count]["exercise"][0]
                            previous_exercise_id_query = (
                                db.session.query(Exercise.exercise_id)
                                .filter_by(exercise_name=previous_exercise)
                                .first()
                            )

                            update_databse_exercise = (
                                db.session.query(WorkoutExercises)
                                .filter_by(
                                    workout_id=workouts_id[day],
                                    exercise_id=previous_exercise_id_query.exercise_id,
                                )
                                .update({"exercise_id": exercise_id_query.exercise_id})
                            )
                        except IndexError as ie:
                            print(f"you are out of range {ie}")

            # Catch change in sets
            if x.startswith(f"sets_{day}"):
                count_sets += 1
                exe_sets = submitted_data[x]

                if exercise_id_query:
                    current_workout_exercise_sets = (
                        db.session.query(WorkoutExercises.prescribed_sets)
                        .filter_by(
                            workout_id=workouts_id[day],
                            exercise_id=current_exercise_id,
                        )
                        .first()
                    )

                    if current_workout_exercise_sets:
                        update_databse_sets = (
                            db.session.query(WorkoutExercises)
                            .filter_by(
                                workout_id=workouts_id[day],
                                exercise_id=current_exercise_id,
                            )
                            .update({"prescribed_sets": exe_sets})
                        )

            # Catch change in pauses
            if x.startswith(f"pauses_{day}"):
                count_pauses += 1
                exe_pauses = submitted_data[x]
                print(f"day {day}: name: {exe_name} sets:{exe_pauses}")

                if exercise_id_query:
                    current_workout_exercise_pauses = (
                        db.session.query(WorkoutExercises.rest_period)
                        .filter_by(
                            workout_id=workouts_id[day],
                            exercise_id=current_exercise_id,
                        )
                        .first()
                    )

                    if current_workout_exercise_pauses:
                        update_databse_sets = (
                            db.session.query(WorkoutExercises)
                            .filter_by(
                                workout_id=workouts_id[day],
                                exercise_id=current_exercise_id,
                            )
                            .update({"rest_period": exe_pauses})
                        )

        db.session.commit()

# For tryining sessions mainly ---------------------------------------
def add_session_to_db(chosen_day_by_user, workouts_id):
    # After user hits "add set" set session 
    # if session_date != today create new
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    does_session_exist = db.session.query(Sessions.session_date, Sessions.session_id).filter(
        and_(
            Sessions.workout_id == chosen_day_by_user,
            Sessions.user_id == user_id_db,
            func.DATE(Sessions.session_date) == func.DATE(NOW)
        )
    ).first()

    if does_session_exist:
        print_string = ("Sorry, there is already workout session for today")
    else:        
        workout_id_hopefully = workouts_id[chosen_day_by_user]

        # There is no session today, create a new one
        check_session_existance = db.session.query(Sessions.session_id).filter(
            Sessions.user_id == user_id_db,
            Sessions.workout_id == workout_id_hopefully,
            func.DATE(Sessions.session_date) == func.DATE(NOW)
        ).first()

        if not check_session_existance:
            new_session_query = Sessions(user_id=user_id_db, workout_id=workout_id_hopefully, notes="Null")
            db.session.add(new_session_query)


            # Also add data to session_mesocycles
            training_day_number_query = db.session.query(Sessions).filter(
                Sessions.user_id == user_id_db,
                Sessions.workout_id == chosen_day_by_user,
            ).count()

            mesocycle_id_query = db.session.query(Mesocycles.mesocycle_id).filter(
                Mesocycles.user_id ==user_id_db,
            ).order_by(desc(Mesocycles.mesocycle_id)).first()

            session_id_query = db.session.query(Sessions.session_id).filter(
                Sessions.user_id == user_id_db,
                Sessions.workout_id == workout_id_hopefully,
                
            )

            session_id_result = session_id_query[0] if session_id_query else None

            # Access result like this: session_id_query[0][0]
            if does_session_exist:
                pass
            else:
                try:
                    if session_id_result is not None:
                        new_session_mesocycles_query = SessionMesocycles(
                        session_id=session_id_result[0],
                        mesocycle_id=mesocycle_id_query[0], 
                        training_day_number=training_day_number_query)

                        db.session.add(new_session_mesocycles_query)
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    return redirect(url_for("training_session"))

    # Find if there are relevant exercise's sets - return for jinja
    last_session_query = db.session.query(Sessions.session_id).filter(
        Sessions.user_id == user_id_db,
        func.DATE(Sessions.session_date) == func.DATE(NOW),
        Sessions.workout_id ==workout_id_hopefully
    ).order_by(desc(Sessions.session_date)).first()

    if last_session_query:
        sets_for_jinja = db.session.query(ExerciseEntries).filter(
            ExerciseEntries.session_id == last_session_query[0]
        ).all()

        return sets_for_jinja
        

def find_exercise_id_db(exercise):
    find_exercise_query = db.session.query(Exercise.exercise_id).filter(
        Exercise.exercise_name == exercise
    ).first()

    if find_exercise_query:
        return find_exercise_query

def add_set_to_db(submitted_data, exercise, sets_for_jinja, chosen_day, workout_names) -> dict:
    user = Users.query.filter_by(username=current_user.username).first()
    user_id_db = user.user_id

    if exercise is not None:
        workout_id_from_db = (
                            db.session.query(WorkoutPlan.workout_id)
                            .filter(
                                WorkoutPlan.user_id==user_id_db,
                                WorkoutPlan.workout_name==chosen_day
                            )
                            .order_by(desc(WorkoutPlan.created_at)).first()
                        )
        
        # Add set to database - exercise_entries
        # SELECT session_id FROM Sessions WHERE workout_id = my_workout_id ORDER BY session_id DESC
        if workout_id_from_db[0] is not None:
            session_id_form_db = db.session.query(Sessions.session_id).filter(
                Sessions.workout_id == workout_id_from_db[0]
            ).first()
            
            exe_id = find_exercise_id_db(exercise)          
            
            try:
                # Find total sets in ExerciseEntries
                sets_yet = db.session.query(ExerciseEntries.set_number).filter(
                    ExerciseEntries.session_id == session_id_form_db[0],
                    ExerciseEntries.exercise_id == exe_id[0]
                ).count()
            except TypeError:
                print("Bro, there is no session yet, but I will set 0 for you")
                sets_yet = 0

            sets_yet += 1

            # Save exdrcise entry into database
            try:
                exercise_entry_add = ExerciseEntries(
                            session_id=session_id_form_db[0], 
                            exercise_id=exe_id[0], 
                            set_number=sets_yet, 
                            reps=int(submitted_data.get("reps", 0)), 
                            weight=float(submitted_data.get("kg", 0.0)), 
                            rpe=int(submitted_data.get("rpe", 0)),
                            notes=submitted_data.get("notes", "")
                        )
                db.session.add(exercise_entry_add)
                db.session.commit()
            except Exception as e:
                print(f"Exception line cca 573: {e}")

# Sets for jinja
def jinja_sets_function(sets_for_jinja):
    print("Hi I am inside sets for jinja function :-)")        
        

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
        print(f"test: {form.password.data}")
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


@app.route("/workout_plan_page", methods=["GET"])
@login_required
def workout_plan_page():
    selected_mesocycle = request.args.get("mesocycle")
    connection = db.session.connection()
    inspect_db_names = inspect(db.engine)
    tables = inspect_db_names.get_table_names()
    any_string_contains_word = [
        item
        for item in tables
        if f"{current_user.username}_M{selected_mesocycle}" in item
    ]
    amount_of_tables_curr_meso = len(any_string_contains_word)

    # Load amount of mesocycles
    all_users_mesocycles_query = Users.query.filter_by(
        username=current_user.username
    ).first()
    try:
        all_users_mesocycles = int(all_users_mesocycles_query.mesocycles)
    except TypeError:
        return render_template("table_layout.html", year=YEAR)

    nested_exercises_list = []

    for table in any_string_contains_word:
        exercises_query = text(
            f"""
        SELECT * FROM {table}
        ORDER BY exercise
        """
        )
        exercises_result = connection.execute(exercises_query).fetchall()
        nested_exercises_list.append(exercises_result)

    # If no value exists or none is selected, just don't give me table, show only select bar
    number_for_loop_separation = 0  # Default value
    try:
        exercises_per_session_query = text(
            f"""
        SELECT exercise FROM {any_string_contains_word[0]}
        """
        )
        exercises_per_session = connection.execute(exercises_per_session_query)
        number_for_loop_separation = sum(1 for _ in exercises_per_session)
    except IndexError as e:
        print("No workout is selected or workout doesn't exists")

    connection.close()

    return render_template(
        "workout.html",
        tables_for_las_meso=any_string_contains_word,
        full_meso_tables_names=any_string_contains_word,
        for_loop=number_for_loop_separation,
        amount_of_mesocycles=all_users_mesocycles,
        nested_exercises_list=nested_exercises_list,
        length_curr_meso=len(nested_exercises_list),
        year=YEAR,
    )


# ----------------------------------------------------------------------


@app.route("/table_layout", methods=["GET", "POST"])
@login_required
def table_layout():
    if current_user.is_authenticated:
        # Retrieve the user record once
        user = Users.query.filter_by(username=current_user.username).first()
        if user:
            # If 'mesocycles' is None, set it to 0 for easier work in the future
            if user.mesocycles is None:
                # I deactivated this for testing purposes
                """user.mesocycles = 0
                db.session.commit()"""

            username = current_user.username

            if request.method == "POST":
                meso_name = request.form.get("meso_name")
                meso_duration = request.form.get("mesocycle")
                workouts_per_week = request.form.get("per_week")

                # Save to DB
                user_from_db = Users.query.filter_by(
                    username=current_user.username
                ).first()
                user_id = user_from_db.user_id
                mesocycles_db = Mesocycles(
                    name=meso_name,
                    user_id=user_id,
                    mesocycle_duration_weeks=meso_duration,
                    workouts_per_week=workouts_per_week,
                )

                # Create rows in WorkoutPlan / workouts based on workout_per_week ... Workout name default to number of weeks
                # INSERT INTO workouts (user_id, workout_name) VALUES (CurrentUser.username, meso_name)
                for i in range(int(workouts_per_week)):
                    user = Users.query.filter_by(username=current_user.username).first()
                    user_id_db = user.user_id
                    table = WorkoutPlan(
                        workout_name=i,
                        user_id=user_id_db,
                    )

                    db.session.add(table)

                db.session.add(mesocycles_db)
                db.session.commit()

            # Before we let our users create new table we need to restrict his access to DB so no SQL injections are possible
            if not re.match(r"^\w+$", username):
                return jsonify({"error": "Invalid username"})

        return redirect("create_workout")
    return render_template("table_layout.html", year=YEAR)


# Here is created mesocycle workout
@app.route("/create_workout", methods=["GET", "POST"])
@login_required
def create_workout():
    # Delete function
    def delete_exercise(submitted_data):
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


    # Add exercise to database --- add weekly to arguments
    def add_exercise(submitted_data, order, weekly, jinja_exercises):
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

    # Create workout name / tag - user can change workout name in database
    def find_workout_name_from_user(submitted_data, weekly) -> None:
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

    weekly, workout_names, workouts_id = find_users_weeks()

    # Default order
    order, jinja_exercises = default_order(weekly)

    exercises_for_jinja(jinja_exercises, weekly, workouts_id)

    if request.method == "GET":
        # Handle AJAX request for exercise search
        search_term = request.args.get("query")

        if search_term:  # This will be triggered by the AJAX call
            exercises = Exercise.query.filter(
                Exercise.exercise_name.ilike(f"%{search_term}%")
            ).all()
            exercise_names = [exercise.exercise_name for exercise in exercises]
            return jsonify(exercise_names)  # Return JSON for AJAX request

    elif request.method == "POST":
        # Process form submission and save the workout data
        submitted_data = request.form.to_dict()

        # Name of workout is default set 1-x and user can change it
        workout_names = find_workout_name_from_user(submitted_data, weekly)

        # Save new exercise into database - return order number
        exercises_dict = add_exercise(submitted_data, order, weekly, jinja_exercises)

        # Call function to delete exercise from workout
        delete_exercise(submitted_data)

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
    sets_for_jinja = {}    
    # Function to acces workout day / data from database
    weekly, workout_names, workout_id = find_users_weeks()
    order, jinja_exercises = default_order(weekly)
    jinja_exe = exercises_for_jinja(jinja_exercises, weekly, workout_id)

    workouts_id_name = {}
    # Make dick like this: 1: "Upper Body"
    for i in range(weekly):
        workouts_id_name[i] = workout_names[i]  

    chosen_day = session.get("chosen_day")
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
            if load_chosen_exercise=="":
                session.pop("chosen_exercise", None)
                load_chosen_exercise = None
            else:
                session["chosen_exercise"] = load_chosen_exercise
                chosen_exercise = load_chosen_exercise


    elif request.method == "POST":
        sets_for_jinja = add_session_to_db(workout_key, workout_id)

        print(sets_for_jinja)

        submitted_data = request.form.to_dict()

        add_set_to_db(submitted_data, chosen_exercise, sets_for_jinja, chosen_day, workout_names)
        
        jinja_sets_function(sets_for_jinja)


    return render_template(
        "training_session.html",
        today=DATE,
        year=YEAR,
        w_names=workouts_id_name,
        weeks=weekly,
        chosen_day=chosen_day,
        exercises_to_display=exercises_in_workout,
        chosen_exercise=chosen_exercise,
        sets_for_jinja=sets_for_jinja
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
    # Get info from HTML submit and keep it after reload, or hitting submit button. Delete session if we are out of range.
    try:
        if request.args.get("training_day") is not None:
            choose_training_day = int(request.args.get("training_day"))
            session["choose_training_day"] = choose_training_day
        elif "choose_training_day" in session:
            choose_training_day = session["choose_training_day"]
        else:
            choose_training_day = 0
    except OperationalError:
        session.clear()
        if request.args.get("training_day") is not None:
            choose_training_day = int(request.args.get("training_day"))
            session["choose_training_day"] = choose_training_day
        elif "choose_training_day" in session:
            choose_training_day = session["choose_training_day"]
        else:
            choose_training_day = 0

    # Title for table
    table_title = 1
    if choose_training_day is not None:
        table_title += int(choose_training_day)
    else:
        table_title = 1

    # Logic for training sessions---------------------------------------------------------------------------

    # Access current users's mesocycles - if none is picked by users - show workout day one
    users = Users.query.filter_by(username=current_user.username).first()
    last_masocycle = users.mesocycles

    # SQL query to fetch the latest entry for each exercise in the original order
    sql_query = text(
        f"""
        WITH latest_exercises AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY exercise ORDER BY id DESC) AS row_num
            FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
        ),
        initial_order AS (
            SELECT exercise, MIN(id) AS first_id
            FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
            GROUP BY exercise
        )
        SELECT le.*
        FROM latest_exercises le
        JOIN initial_order io ON le.exercise = io.exercise
        WHERE le.row_num = 1
        ORDER BY io.first_id
    """
    )

    inspect_db_names = inspect(db.engine)
    connection = db.session.connection()
    connection.commit()
    try:
        execute_sql = connection.execute(sql_query)
    except OperationalError:
        try:
            sql_query = text(
                f""" 
                SELECT exercise, sets, pauses
                FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
            """
            )
        except OperationalError:

            # If new users with empty mesocycles, he will be redirected to workout page
            return render_template("table_layout.html")

    # From last mesocycle load all tables
    list_of_all_tables = inspect_db_names.get_table_names()
    tables_from_last_meso = []

    for table in list_of_all_tables:
        if table.startswith(f"{current_user.username}_M{last_masocycle}"):
            tables_from_last_meso.append(table)

    # Separate query just to store chosen day from users
    try:
        current_training_day_sql = text(
            f"""
        SELECT exercise FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
        """
        )
        current_training_day = connection.execute(current_training_day_sql)
        list_of_current_exerxises: list = []
        for exercise in current_training_day:
            list_of_current_exerxises.append(exercise[0])
    except OperationalError:
        current_training_day = 1
        execute_sql = []

    # Load data from users-----------------------------------------------------------------------------------

    if request.method == "POST":
        form_data = request.form
        num_rows = (
            len(form_data) // 6
        )  # Assuming 6 fields per row: 3 hidden and 3 visible
        # Values for new exercise
        new_exercise = form_data.get("new_exercise")
        new_sets = form_data.get("new_sets")
        new_pauses = form_data.get("new_pauses")

        for i in range(1, num_rows + 1):
            exercise_id = form_data.get(f"add_exercise{i}")
            sets_id = form_data.get(f"add_sets{i}")
            pauses_id = form_data.get(f"add_pauses{i}")
            exercise_value = form_data.get(f"exercise{i}")
            sets_value = form_data.get(f"sets{i}")
            pauses_value = form_data.get(f"pauses{i}")

            try:
                if exercise_value or sets_value or pauses_value:
                    # If users won't give any values but hit enter it will load previous data
                    exercise_value = (
                        exercise_id if exercise_value == "" else exercise_value
                    )
                    sets_value = sets_id if sets_value == "" else sets_value
                    pauses_value = pauses_id if pauses_value == "" else pauses_value

                    replace_exercise_query = text(
                        f"""
                    UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                    SET exercise='{exercise_value}', sets='{sets_value}', pauses='{pauses_value}'
                    WHERE id = (
                        SELECT max(id)
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{exercise_id}'
                    )
                    """
                    )
                    connection.execute(replace_exercise_query)

                connection.commit()

            except OperationalError as op:
                print(f"You did poorly {op}")
                return redirect(url_for("profile"))
            # Make SQL query and replace old exercise with a new one
        try:
            if new_exercise:
                # If users forget to give sets or pauses they will be set to 0
                new_sets = 0 if new_sets == "" else new_sets
                new_pauses = 0 if new_pauses == "" else new_pauses

                add_new_exercise = text(
                    f"""
                        INSERsT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (exercise, sets, pauses)
                        VALUES ('{new_exercise}', '{new_sets}', '{new_pauses}')
                        """
                )
                connection.execute(add_new_exercise)
                connection.commit()
        except OperationalError:
            print(f"Here should be log {OperationalError}")
    return render_template(
        "profile.html",
        exercises_meso_one=execute_sql,
        training_sessions=tables_from_last_meso,
        training_session_length=len(tables_from_last_meso),
        table_title=table_title,
        today=DATE,
        year=YEAR,
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
