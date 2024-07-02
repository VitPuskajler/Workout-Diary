from datetime import datetime
import re

from flask import Flask, render_template, request, redirect, url_for, session, flash, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import Integer, String, Float, Column, inspect, create_engine, text, MetaData
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict

NOW = datetime.now()
DATE = NOW.strftime("%d%m%Y")
YEAR = NOW.strftime("%Y")

app = Flask(__name__)
app.secret_key = "thiskeyshouldntbeherebutfornowitisok.1084"

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Database setup
class Base(DeclarativeBase):
    pass

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///workout_plan_01.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create engine so I can work with dynamic tables
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
metadata = MetaData()

db = SQLAlchemy(model_class=Base)

db.init_app(app)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    age = Column(Integer, unique=False, nullable=False)
    weight = Column(Float, nullable=False)
    mesocycles = Column(Integer, nullable=True)

    def __init__(self, username, password, age, weight):
        self.username = username
        self.password = password
        self.age = age
        self.weight = weight
        

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class WorkoutPlan(db.Model):
    id = db.Column(db.String, primary_key=True)
    exercise = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    pauses = db.Column(db.Integer, nullable=False)
    first_set = db.Column(db.Integer)
    weight_first_set = db.Column(db.Float)
    rpe_first_set = db.Column(db.Float)
    second_set = db.Column(db.Integer)
    weight_second_set = db.Column(db.Float)
    rpe_second_set = db.Column(db.Float)
    third_set = db.Column(db.Integer)
    weight_third_set = db.Column(db.Float)
    rpe_third_set = db.Column(db.Float)
    notes = db.Column(db.String)

    def __repr__(self):
        return f"<WorkoutPlan {self.excercise}>"

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password')
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=0)])
    weight = FloatField('Weight', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

# --------------------------------------------------------------------------------------------------------------------------------------


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_password, age=form.age.data, weight=form.weight.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index_page'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index_page'))

@app.route('/home')
def home():
    return redirect(url_for('index_page'))

@app.route("/")
def index_page():
    if current_user.is_authenticated:
        username = current_user.username
    else:
        username = None
    return render_template("index.html", user=username, year=YEAR)

# Workout Plan ---------------------------------------------------------

@app.route('/workout_plan')
@login_required
def workout_plan():
    return redirect(url_for('workout_plan_page'))

@app.route('/workout_plan_page', methods=["GET"])
@login_required
def workout_plan_page():
    selected_mesocycle = request.args.get('mesocycle')
    connection = db.session.connection()
    inspect_db_names = inspect(db.engine)
    tables = inspect_db_names.get_table_names()
    any_string_contains_word = [item for item in tables if f"{current_user.username}_M{selected_mesocycle}" in item] 
    amount_of_tables_curr_meso = len(any_string_contains_word)
    
    # Load amount of mesocycles
    all_users_mesocycles_query = User.query.filter_by(username=current_user.username).first()
    try:
        all_user_mesocycles = int(all_users_mesocycles_query.mesocycles)
    except TypeError:
        return render_template("table_layout.html", year=YEAR)

    nested_exercises_list = []

    for table in any_string_contains_word:
        exercises_query = text(f"""
        SELECT * FROM {table}
        ORDER BY exercise
        """)
        exercises_result = connection.execute(exercises_query).fetchall()
        nested_exercises_list.append(exercises_result)
            
    # If no value exists or none is selected, just don't give me table, show only select bar
    number_for_loop_separation = 0  # Default value
    try:
        exercises_per_session_query = text(f"""
        SELECT exercise FROM {any_string_contains_word[0]}
        """)
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
        amount_of_mesocycles=all_user_mesocycles,
        nested_exercises_list=nested_exercises_list,
        length_curr_meso=len(nested_exercises_list),
        year=YEAR
        
    )

# ----------------------------------------------------------------------

@app.route('/table_layout', methods=['GET', 'POST'])
@login_required
def table_layout():
    if current_user.is_authenticated:
            user_mesocycles = text(f"""
            SELECT mesocycles FROM users
            WHERE username = '{current_user.username}'
            """)
            connection = db.session.connection()
            total_meso = connection.execute(user_mesocycles).fetchone
            try:
                if total_meso[0] is None:
                    user_mesocycles = 0
            except TypeError:
                user_mesocycles = 1

    if request.method == "POST":
        exrs = request.form.get("xcrs")
        planned_exrs = request.form.get("weekly")
        mesocycle = request.form.get("mesocycle")
        deload = request.form.get("deload")
        date = "0"
        
        # Set value of mesocycles to 0 for easier work in future
        user = User.query.filter_by(username=current_user.username).first()
        if user and (user.mesocycles is None):
            user.mesocycles = 0
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
                cell_value = ''  # <- This can be adjusted as needed
                row_data.append(cell_value)
            table_data.append(row_data)

        session["table_data"] = table_data
        session["weekly"] = per_week
        session["starter"] = starter
        session['excercise'] = exrs

        username = current_user.username
        
        # Handle current user's mesocycles passing to jinja2
        print(user.mesocycles)

        # Before we let our user create new table we need to restrict his access to DB so no SQL injections are possible
        if not re.match(r'^\w+$', username) :
            return jsonify({"error": "Invalid username"})       

        return redirect("create_workout")
    return render_template("table_layout.html", 
                           user_meso=user_mesocycles,
                           year=YEAR
                           )

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
                parts = key.split('_')
                table_index = int(parts[1])
                row_index = int(parts[3])
                col_index = int(parts[5])

                if table_index not in submitted_data:
                    submitted_data[table_index] = {}
                if row_index not in submitted_data[table_index]:
                    submitted_data[table_index][row_index] = {}

                submitted_data[table_index][row_index][col_index] = value

        # Create as many tables as I have sessions per week
        def create_tables_dynamically():
            user = User.query.filter_by(username=current_user.username).first()
            if user and (user.mesocycles is None):
                user.mesocycles = 0
                db.session.commit()
            elif user.mesocycles >= 1: 
                user.mesocycles += 1
                db.session.commit()
            elif user and (user.mesocycles == 0 or user.mesocycles < 1):
                user.mesocycles = 1
                db.session.commit()
        
            for one_session in range(int(weekly)):  
                table_name = f"{current_user.username}_M{user.mesocycles}_{one_session}"
                sql = text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY,
                    date TEXT,
                    exercise TEXT NOT NULL,
                    sets INTEGER NOT NULL,
                    pauses FLOAT NOT NULL,
                    first_set INTEGER,
                    weight_first_set FLOAT,
                    rpe_first_set FLOAT,
                    second_set INTEGER,
                    weight_second_set FLOAT,
                    rpe_second_set FLOAT,
                    third_set INTEGER, 
                    weight_third_set FLOAT,
                    rpe_third_set FLOAT,
                    notes TEXT
                )
                """)

                try:
                    connection = db.session.connection()
                    connection.execute(sql)
                    print(f"Table '{table_name}' created successfully!")        
                except Exception as e:
                    print(f"Error creating table '{table_name}': {e}")


                # Save exercises to corresponding tables
                # Chosen exercises, sets and reps
                for exercise in range(int(exercises_per_session)):
                    
                    current_ecercise = submitted_data[one_session][exercise][0]
                    current_sets = submitted_data[one_session][exercise][1]
                    current_pause = submitted_data[one_session][exercise][2]
                    
                    try:
                        data = text(f'''
                        INSERT INTO {table_name} (exercise, sets, pauses)
                        VALUES ('{current_ecercise}', {current_sets}, {current_pause})
                        ''')
                        connection = db.session.connection()
                        connection.execute(data)
                        connection.commit()
                        print(f"Saved data into '{table_name}'")
                    except IntegrityError as e:
                        print(f"IntegrityError: {e}")
                    except Exception as e:
                        print(f"Something went wrong and I didn't save your stuff: {e}")
                print(f"length of submitted data = {len(submitted_data)}\nlength of weekly = {weekly}")
        
        create_tables_dynamically()
        return redirect(url_for("workout_plan_page"))

    return render_template("create_workout.html", table_data=table_data, weekly=weekly, st=starter, enumerate=enumerate, year=YEAR)


@app.route('/training_session_redirect', methods=["GET"])
def training_session_redirect():
    return redirect(url_for('training_session'))


# Training session ---------------------------------------------------------

@app.route('/training_session', methods=["GET", "POST"])
@login_required
def training_session():
    # Get info from HTML submit and keep it after reload, or hitting submit button
    if request.args.get('training_day') is not None:
        choose_training_day = int(request.args.get('training_day'))
        session['choose_training_day'] = choose_training_day
    elif 'choose_training_day' in session:
        choose_training_day = session['choose_training_day']
    else:
        choose_training_day = 0

    # Title for table
    table_title = 1
    if choose_training_day is not None:
        table_title += int(choose_training_day)
    else:
        table_title= 1

    # Logic for training sessions---------------------------------------------------------------------------

    # Access current user's mesocycles - if none is picked by user - show workout day one
    user = User.query.filter_by(username=current_user.username).first()
    last_masocycle = user.mesocycles

    # SQL query to fetch the latest entry for each exercise in the original order 
    sql_query = text(f"""
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
    """)

    inspect_db_names = inspect(db.engine)
    connection = db.session.connection()
    try:
        execute_sql = connection.execute(sql_query)
    except OperationalError:
        try:
            sql_query = text(f""" 
                SELECT *
                FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
            """)
        except OperationalError:

            # If new user with empty mesocycles, he will be redirected to workout page
            return render_template("table_layout.html", year=YEAR)

    # From last mesocycle load all tables
    list_of_all_tables = inspect_db_names.get_table_names()
    tables_from_last_meso = []
    
    for table in list_of_all_tables:
        if table.startswith(f"{current_user.username}_M{last_masocycle}"):
            tables_from_last_meso.append(table)
    
    # Separate query just to store chosen day from user
    try:
        current_training_day_sql = text(f"""
        SELECT exercise FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
        """)
        current_training_day = connection.execute(current_training_day_sql)
        list_of_current_exerxises: list = []
        for exercise in current_training_day:
            list_of_current_exerxises.append(exercise[0])
    except OperationalError:
        current_training_day = 1
        execute_sql = []

    # Load data from user-----------------------------------------------------------------------------------
    user_input_into_training = {}
    new_row_data = {}
    existing_entry_id = None
    zero_for_null = 0


    if request.method == "POST":
        form_data = request.form
        
        for key, value in form_data.items():
            if value != "":
                user_input_into_training[key] = value
                new_row_data[key[:-2]] = int(value) if value.isdigit() else value
                exercise_number = int(key[len(key)-1]) - 1

                try:
                    exercise_number_query = text(f"""
                    SELECT id FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    """)
                    exercise_number_new = connection.execute(exercise_number_query).fetchall()
                    connection.commit()
                except OperationalError:
                    exercise_number_query = text(f"""
                    SELECT id FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    """)
                    exercise_number_new = connection.execute(exercise_number_query).fetchall()
                    connection.commit()


                try:
                    # Always add SETS + PAUSES, they are not changing
                    find_sets_pauses_query = text(f"""
                    SELECT sets, pauses FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                    """)
                    find_sets_pauses = connection.execute(find_sets_pauses_query).fetchone()
                    
                    # Check if there is today's date for the current exercise - 2 queries because I had ideas and not so much time
                    check_id_query = text(f"""
                        SELECT id, date
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                        ORDER BY id DESC 
                        LIMIT 1
                    """)
            
                    verify_date = connection.execute(check_id_query, {'date': DATE}).fetchone()

                    check_date_query = text(f"""
                        SELECT date 
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise  = '{list_of_current_exerxises[exercise_number]}'
                        ORDER BY id DESC
                        LIMIT 1
                        """) 
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
                        find_sets_pauses_query = text(f"""
                        SELECT sets, pauses FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{exercise_number}'
                        """)
                        find_sets_pauses = connection.execute(find_sets_pauses_query)

                        # ------------------------------------------------
                        existing_entry_id = verify_date[0]
                        new_row_data['date'] = DATE
                        
                        try:
                            update_query = text(f'''
                                UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                                SET {key[:-2]} = '{value}', date = '{DATE}'
                                WHERE id = (
                                    SELECT MAX(id)
                                    FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                                )
                            ''')
                            new_row_data['id'] = existing_entry_id
                            connection.execute(update_query)
                            connection.commit()
                            print("Updated existing row")
                        # Because sometimes I need to key[:-3] for correct string (exercise name) form
                        except OperationalError:
                            update_query = text(f'''
                                UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                                SET {key[:-3]} = '{value}'
                                WHERE id = (
                                    SELECT MAX(id)
                                    FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                                    WHERE exercise = '{list_of_current_exerxises[exercise_number]}'
                                )
                            ''')
                            new_row_data['id'] = existing_entry_id
                            connection.execute(update_query)
                            connection.commit()
                        print("Updated existing row")
                        
                     # Insert new row if no entry exists for today's date
                    elif zero_for_null == 3:
                        sets_sticks  = find_sets_pauses[0]
                        pauses_sticks = find_sets_pauses[1]
                        try:
                            # Try to do it by raw sql, no fancy joins 
                            insert_query = text(f"""
                            INSERT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (date, exercise, sets, pauses, {key[:-2]})
                            VALUES ('{DATE}', '{list_of_current_exerxises[exercise_number]}', '{sets_sticks}', '{pauses_sticks}', '{value}')
                            """)

                            connection.execute(insert_query)
                            connection.commit()
                        except OperationalError:
                            # Try to do it by raw sql, no fancy joins 
                            insert_query = text(f"""
                            INSERT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (date, exercise, sets, pauses, {key[:-3]})
                            VALUES ('{DATE}', '{list_of_current_exerxises[exercise_number]}', '{sets_sticks}', '{pauses_sticks}', '{value}')
                            """)

                            connection.execute(insert_query)
                            connection.commit()
                        print("Inserted new row")

                except ValueError:
                    print(f"No value such this {key}")
                    


    # ------------------------------------------------------------------------------------------------------

        return redirect(url_for('training_session'))

    return render_template('training_session.html',
                            exercises_meso_one=execute_sql,
                            training_sessions=tables_from_last_meso,
                            training_session_length=len(tables_from_last_meso),
                            table_title=table_title,
                            today=DATE,
                            year=YEAR
                            )

# --------------------------------------------------------------------------

@login_required
@app.route('/execute_workout_plan_exercises')
def execute_workout_plan_exercises(): 
    return render_template("<h1>Just test if process will pass<h1>")

# --------------------------------------------------------------------------
@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    # Get info from HTML submit and keep it after reload, or hitting submit button. Delete session if we are out of range.
    try:
        if request.args.get('training_day') is not None:
            choose_training_day = int(request.args.get('training_day'))
            session['choose_training_day'] = choose_training_day
        elif 'choose_training_day' in session:
            choose_training_day = session['choose_training_day']
        else:
            choose_training_day = 0
    except OperationalError:
        session.clear()
        if request.args.get('training_day') is not None:
            choose_training_day = int(request.args.get('training_day'))
            session['choose_training_day'] = choose_training_day
        elif 'choose_training_day' in session:
            choose_training_day = session['choose_training_day']
        else:
            choose_training_day = 0

    # Title for table
    table_title = 1
    if choose_training_day is not None:
        table_title += int(choose_training_day)
    else:
        table_title= 1

    # Logic for training sessions---------------------------------------------------------------------------

    # Access current user's mesocycles - if none is picked by user - show workout day one
    user = User.query.filter_by(username=current_user.username).first()
    last_masocycle = user.mesocycles

    # SQL query to fetch the latest entry for each exercise in the original order 
    sql_query = text(f"""
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
    """)

    inspect_db_names = inspect(db.engine)
    connection = db.session.connection()
    connection.commit()
    try:
        execute_sql = connection.execute(sql_query)
    except OperationalError:
        try:
            sql_query = text(f""" 
                SELECT exercise, sets, pauses
                FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
            """)
        except OperationalError:

            # If new user with empty mesocycles, he will be redirected to workout page
            return render_template("table_layout.html")

    # From last mesocycle load all tables
    list_of_all_tables = inspect_db_names.get_table_names()
    tables_from_last_meso = []
    
    for table in list_of_all_tables:
        if table.startswith(f"{current_user.username}_M{last_masocycle}"):
            tables_from_last_meso.append(table)
    
    # Separate query just to store chosen day from user
    try:
        current_training_day_sql = text(f"""
        SELECT exercise FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
        """)
        current_training_day = connection.execute(current_training_day_sql)
        list_of_current_exerxises: list = []
        for exercise in current_training_day:
            list_of_current_exerxises.append(exercise[0])
    except OperationalError:
        current_training_day = 1
        execute_sql = []

    # Load data from user-----------------------------------------------------------------------------------

    if request.method == "POST":
        form_data = request.form
        num_rows = (len(form_data) // 6)  # Assuming 6 fields per row: 3 hidden and 3 visible
        # Values for new exercise
        new_exercise = form_data.get("new_exercise")
        new_sets = form_data.get("new_sets")
        new_pauses = form_data.get("new_pauses")

        for i in range(1, num_rows + 1):
            exercise_id = form_data.get(f'add_exercise{i}')
            sets_id = form_data.get(f'add_sets{i}')
            pauses_id = form_data.get(f'add_pauses{i}')
            exercise_value = form_data.get(f'exercise{i}')
            sets_value = form_data.get(f'sets{i}')
            pauses_value = form_data.get(f'pauses{i}')
            
            

            try: 
                if exercise_value or sets_value or pauses_value:
                    # If user won't give any values but hit enter it will load previous data
                    exercise_value = exercise_id if exercise_value == '' else exercise_value
                    sets_value = sets_id if sets_value == '' else sets_value
                    pauses_value = pauses_id if pauses_value == '' else pauses_value
                    

                    replace_exercise_query = text(f"""
                    UPDATE {current_user.username}_M{last_masocycle}_{choose_training_day}
                    SET exercise='{exercise_value}', sets='{sets_value}', pauses='{pauses_value}'
                    WHERE id = (
                        SELECT max(id)
                        FROM {current_user.username}_M{last_masocycle}_{choose_training_day}
                        WHERE exercise = '{exercise_id}'
                    )
                    """)
                    connection.execute(replace_exercise_query)

                connection.commit()
                
            except OperationalError as op:
                print(f"You did poorly {op}")
                return redirect(url_for('profile'))
            # Make SQL query and replace old exercise with a new one
        try:
            if new_exercise:
                        # If user forget to give sets or pauses they will be set to 0
                        new_sets = 0 if new_sets == '' else new_sets
                        new_pauses = 0 if new_pauses == '' else new_pauses

                        add_new_exercise = text(f"""
                        INSERT INTO {current_user.username}_M{last_masocycle}_{choose_training_day} (exercise, sets, pauses)
                        VALUES ('{new_exercise}', '{new_sets}', '{new_pauses}')
                        """)
                        connection.execute(add_new_exercise)
                        connection.commit()       
        except OperationalError:
            print(f"Here should be log {OperationalError}")
    return render_template("profile.html",
                           exercises_meso_one=execute_sql,
                            training_sessions=tables_from_last_meso,
                            training_session_length=len(tables_from_last_meso),
                            table_title=table_title,
                            today=DATE,
                            year=YEAR
                            )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)