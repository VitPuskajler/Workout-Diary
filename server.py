import re
import os
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request,session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import Column, Float, Integer, MetaData, String, DateTime, func, create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import FloatField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange

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

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, "instance/workout.db")}"
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///workout.db"
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
    created_at = Column(DateTime, default=func.now()) # current time / date
    description = Column(String(100), unique=True, nullable=False)

    def __init__(self, user_id, workout_name, description):
        self.user_id = user_id
        self.workout_name = workout_name
        self.description = description
        # created_at is not here because SQLAlchemy will take care of it

# 4. WorkoutExercises Table
class WorkoutExercises(UserMixin, db.Model):
    __tablename__ = "workout_exercises"
    workout_exercise_id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    exercise_id = Column(Integer, db.ForeignKey("exercises.exercise_id"))
    order_in_workout = Column(Integer, unique=True, nullable=False)
    prescribed_sets = Column(Integer, unique=False, nullable=False)
    prescribed_reps = Column(Integer, unique=False, nullable=True)
    rest_period = Column(Integer, unique=False, nullable=False)

    def __init__(self, workout_id, exercise_id, order_in_workout, prescribed_sets, prescribed_reps, rest_period):
        self.workout_id = workout_id
        self.exercise_id = exercise_id
        self.order_in_workout = order_in_workout
        self.prescribed_sets = prescribed_sets
        self.prescribed_reps = prescribed_reps
        self.rest_period = rest_period

# 5. Sessions Table
# High-level information about each workout session, such as the date, user, and overall notes
class Sessions(UserMixin, db.Model):
    __tablename__ = 'sessions'
    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    session_date = Column(DateTime, default=func.now())
    notes = Column(String(150),unique=False, nullable=True)

    def __init__(self, user_id, workout_id, notes):
        self.user_id = user_id
        self.workout_id = workout_id
        self.notes = notes

# 6. ExerciseEntries Table
class ExerciseEntries(UserMixin, db.Model):
    __tablename__ = "exercise_entries"
    entry_id = Column(Integer, primary_key=True)
    session_id = Column(String(100), db.ForeignKey("sessions.session_id"))
    exercise_id = Column(Integer, db.ForeignKey("exercises.exercise_id"))
    set_number = Column(Integer, unique=True, nullable=False)
    reps = Column(Integer, unique=False, nullable=True)
    weight = Column(Float, unique=False, nullable=True)
    rpe = Column(Float, unique=False, nullable=True)
    notes = Column(String(150), unique=False, nullable=True)

# 7. Mesocycles Table
class Mesocycles(UserMixin, db.Model):
    __tablename__ = "mesocycles"
    mesocycle_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    username = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), unique=False, nullable=False)
    mesocycle_duration_weeks = Column(Integer, unique=False, nullable=False)

    def __init__(self, user_id, name, mesocycle_duration_weeks):
        self.user_id = user_id
        self.name = name
        self.mesocycle_duration_weeks = mesocycle_duration_weeks

# 8. SessionMesocycles Table
# Links sessions to mesocycles, allowing tracking of training days within a mesocycle
class SessionMesocycles(UserMixin, db.Model):
    __tablename__ = "session_mesocycles"
    session_id = Column(Integer, db.ForeignKey("sessions.session_id"), primary_key=True)
    mesocycle_id = Column(Integer, db.ForeignKey("mesocycles.mesocycle_id"), primary_key=True)
    training_day_number = Column(Integer, unique=False, nullable=False)


    def __init__(self, session_id, mesocycle_id, training_day_number):
        self.session_id = session_id
        self.mesocycle_id = mesocycle_id
        self.training_day_number = training_day_number


@login_manager.user_loader
def load_users(user_id):
    return Users.query.get(int(user_id))


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
            email = form.email.data,
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
        users_mesocycles = text(
            f"""
            SELECT mesocycles FROM users
            WHERE username = '{current_user.username}'
            """
        )
        connection = db.session.connection()
        total_meso = connection.execute(users_mesocycles).fetchone
        try:
            if total_meso[0] is None:
                users_mesocycles = 0
        except TypeError:
            users_mesocycles = 1

    if request.method == "POST":
        exrs = request.form.get("xcrs")
        planned_exrs = request.form.get("weekly")
        mesocycle = request.form.get("mesocycle")
        deload = request.form.get("deload")
        date = "0"

        # Set value of mesocycles to 0 for easier work in future
        users = Users.query.filter_by(username=current_user.username).first()
        if users and (users.mesocycles is None):
            users.mesocycles = 0
            db.session.commit()

        try:
            per_week = int(request.form.get("weekly", 0))
            if per_week <= 0:
                raise ValueError("Weekly value must be greater than zero.")
        except (TypeError, ValueError) as e:
            return "Invalid input for 'weekly': " + str(e), 400

        num_rows = int(request.form["xcrs"])
        num_cols = 3

        table_data = []
        for i in range(num_rows):
            row_data = []
            starter = 0
            for j in range(num_cols):
                cell_value = ""  # <- This can be adjusted as needed
                row_data.append(cell_value)
            table_data.append(row_data)

        session["table_data"] = table_data
        session["weekly"] = per_week
        session["starter"] = starter
        session["excercise"] = exrs

        username = current_user.username

        # Handle current users's mesocycles passing to jinja2
        print(users.mesocycles)

        # Before we let our users create new table we need to restrict his access to DB so no SQL injections are possible
        if not re.match(r"^\w+$", username):
            return jsonify({"error": "Invalid username"})

        return redirect("create_workout")
    return render_template("table_layout.html", users_meso=users_mesocycles, year=YEAR)


# Here is created mesocycle workout
@app.route("/create_workout", methods=["GET", "POST"])
@login_required
def create_workout():
    table_data = session.get("table_data", [])
    weekly = session.get("weekly", 0)
    starter = session.get("starter", 0)
    current_table = session.get("current_user_table")
    exercises_per_session = session.get("excercise")

    if request.method == "POST":
        submitted_data = {}

        for key, value in request.form.items():
            if key.startswith("table_"):
                parts = key.split("_")
                table_index = int(parts[1])
                row_index = int(parts[3])
                col_index = int(parts[5])

                if table_index not in submitted_data:
                    submitted_data[table_index] = {}
                if row_index not in submitted_data[table_index]:
                    submitted_data[table_index][row_index] = {}

                submitted_data[table_index][row_index][col_index] = value

        # Create as many tables as I have sessions per week


@app.route("/training_session_redirect", methods=["GET"])
def training_session_redirect():
    return redirect(url_for("training_session"))


# Training session ---------------------------------------------------------


@app.route("/training_session", methods=["GET", "POST"])
@login_required
def training_session():
    # Get info from HTML submit and keep it after reload, or hitting submit button
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
    try:
        execute_sql = connection.execute(sql_query)
    except OperationalError:
        try:
            sql_query = text(
                f""" 
                SELECT *
                FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
            """
            )
        except OperationalError:

            # If new users with empty mesocycles, he will be redirected to workout page
            return render_template("table_layout.html", year=YEAR)

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
    users_input_into_training = {}
    new_row_data = {}
    existing_entry_id = None
    zero_for_null = 0

    if request.method == "POST":
        form_data = request.form

        for key, value in form_data.items():
            if value != "":
                users_input_into_training[key] = value
                new_row_data[key[:-2]] = int(value) if value.isdigit() else value
                exercise_number = int(key[len(key) - 1]) - 1

                try:
                    exercise_number_query = text(
                        f"""
                    SELECT id FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    """
                    )
                    exercise_number_new = connection.execute(
                        exercise_number_query
                    ).fetchall()
                    connection.commit()
                except OperationalError:
                    exercise_number_query = text(
                        f"""
                    SELECT id FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    """
                    )
                    exercise_number_new = connection.execute(
                        exercise_number_query
                    ).fetchall()
                    connection.commit()

                try:
                    # Always add SETS + PAUSES, they are not changing
                    find_sets_pauses_query = text(
                        f"""
                    SELECT sets, pauses FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                    """
                    )
                    find_sets_pauses = connection.execute(
                        find_sets_pauses_query
                    ).fetchone()

                    # Check if there is today's date for the current exercise - 2 queries because I had ideas and not so much time
                    check_id_query = text(
                        f"""
                        SELECT id, date
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                        ORDER BY id DESC 
                        LIMIT 1
                    """
                    )

                    verify_date = connection.execute(
                        check_id_query, {"date": DATE}
                    ).fetchone()

                    check_date_query = text(
                        f"""
                        SELECT date 
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise  = '{list_of_current_exerxises[exercise_number]}'
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    )
                    check_date = connection.execute(check_date_query).fetchone()

                    # How to handle "object is not subscriptable"
                    if check_date[0] is None:
                        zero_for_null = 1
                    elif check_date[0] == DATE:
                        zero_for_null = 2
                    else:
                        zero_for_null = 3

                    if zero_for_null == 1 or zero_for_null == 2:
                        # Always add SETS + PAUSES, they are not changing
                        find_sets_pauses_query = text(
                            f"""
                        SELECT sets, pauses FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{exercise_number}'
                        """
                        )
                        find_sets_pauses = connection.execute(find_sets_pauses_query)

                        # ------------------------------------------------
                        existing_entry_id = verify_date[0]
                        new_row_data["date"] = DATE

                        try:
                            update_query = text(
                                f"""
                                UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                                SET {key[:-2]} = '{value}', date = '{DATE}'
                                WHERE id = (
                                    SELECT MAX(id)
                                    FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                                )
                            """
                            )
                            new_row_data["id"] = existing_entry_id
                            connection.execute(update_query)
                            connection.commit()
                            print("Updated existing row")
                        # Because sometimes I need to key[:-3] for correct string (exercise name) form
                        except OperationalError:
                            update_query = text(
                                f"""
                                UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                                SET {key[:-3]} = '{value}'
                                WHERE id = (
                                    SELECT MAX(id)
                                    FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                                )
                            """
                            )
                            new_row_data["id"] = existing_entry_id
                            connection.execute(update_query)
                            connection.commit()
                        print("Updated existing row")

                    # Inserst new row if no entry exists for today's date
                    elif zero_for_null == 3:
                        sets_sticks = find_sets_pauses[0]
                        pauses_sticks = find_sets_pauses[1]
                        try:
                            # Try to do it by raw sql, no fancy joins
                            inserst_query = text(
                                f"""
                            INSERsT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (date, exercise, sets, pauses, {key[:-2]})
                            VALUES ('{DATE}', '{list_of_current_exerxises[exercise_number]}', '{sets_sticks}', '{pauses_sticks}', '{value}')
                            """
                            )

                            connection.execute(inserst_query)
                            connection.commit()
                        except OperationalError:
                            # Try to do it by raw sql, no fancy joins
                            inserst_query = text(
                                f"""
                            INSERsT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (date, exercise, sets, pauses, {key[:-3]})
                            VALUES ('{DATE}', '{list_of_current_exerxises[exercise_number]}', '{sets_sticks}', '{pauses_sticks}', '{value}')
                            """
                            )

                            connection.execute(inserst_query)
                            connection.commit()
                        print("Insersted new row")

                except ValueError:
                    print(f"No value such this {key}")

        # ------------------------------------------------------------------------------------------------------

        return redirect(url_for("training_session"))

    return render_template(
        "training_session.html",
        exercises_meso_one=execute_sql,
        training_sessions=tables_from_last_meso,
        training_session_length=len(tables_from_last_meso),
        table_title=table_title,
        today=DATE,
        year=YEAR,
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
