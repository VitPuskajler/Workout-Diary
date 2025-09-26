import os
from datetime import datetime, timedelta
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from sqlalchemy import (
    MetaData,
    func,
    create_engine,
    desc,
)
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import FloatField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, NumberRange

from db_setup import db
from models.models import Users, WorkoutPlan, Mesocycles, load_user
from workout_management.workout_management import  WorkoutManagement

app = Flask(__name__, instance_relative_config=True)
app.secret_key = "thiskeyshouldntbeherebutfornowitisok.1084"

# Login manager setup
login_manager = LoginManager()
login_manager.user_loader(load_user) 
login_manager.init_app(app)
login_manager.login_view = "login"

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

db.init_app(app)

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
db_operations = WorkoutManagement()

# We are ssigning methods to variables so no () at the end
current_user_id_db = db_operations.current_user_id_db
find_users_weeks = db_operations.find_users_weeks
exercises_for_jinja = db_operations.exercises_for_jinja
default_order = db_operations.default_order
overwrite_exercise = db_operations.overwrite_exercise
find_workout_name_from_user = db_operations.find_workout_name_from_user
add_exercise = db_operations.add_exercise
delete_exercise = db_operations.delete_exercise
add_session_to_db = db_operations.add_session_to_db
find_exercise_id_db = db_operations.find_exercise_id_db
find_exercise_name_db = db_operations.find_exercise_name_db
add_set_to_db = db_operations.add_set_to_db
repeat_set = db_operations.repeat_set
jinja_sets_function = db_operations.jinja_sets_function
delete_set = db_operations.delete_set
exercise_preview = db_operations.exercise_preview
modify_set = db_operations.modify_set
sets_to_do = db_operations.sets_to_do
current_exercise_info = db_operations.current_exercise_info
show_tables_to_user = db_operations.show_tables_to_user
tables_informations = db_operations.tables_informations
workout_day_information = db_operations.workout_day_information
exercise_progress_data = db_operations.exercise_progress_data
fetch_exercise_suggestions = db_operations.fetch_exercise_suggestions
get_today_intuitive_traing = db_operations.get_today_intuitive_traing
create_custom_workout_exercise = db_operations.create_custom_workout_exercise
add_intuitive_exercise = db_operations.add_intuitive_exercise
check_c_session = db_operations.check_c_session
create_custom_session = db_operations.create_custom_session
create_custom_workout_plan = db_operations.create_custom_workout_plan
load_custom_exercises_for_day = db_operations.load_custom_exercises_for_day
exercises_progress = db_operations.exercises_progress
data_for_graph= db_operations.data_for_graph
statistics_for_exercise = db_operations.statistics_for_exercise
all_exercises_list = db_operations.all_exercises_list
last_custom_day = db_operations.last_custom_day
workout_to_excel = db_operations.workout_to_excel
last_mesocycle_by_default = db_operations.last_mesocycle_by_default
user_last_session_id = db_operations.user_last_session_id
last_exercise_preview = db_operations.last_exercise_preview

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
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)

            next_page = request.args.get("next") or request.form.get("next")

            # Fix: ignore invalid values
            if next_page and next_page != "None":
                return redirect(next_page)

            return redirect(url_for("index_page"))

    return render_template("login.html", form=form, next=request.args.get("next"))

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
    dropdown_menu_info = None
    chosen_mesocycle = None
    table_population = None
    
    try:
        if all_users_mesocycles_query:
            dropdown_menu_info = show_tables_to_user(current_user_id)
            try:
                chosen_mesocycle = submitted_data.get("mesocycle")
                if chosen_mesocycle:
                    session["chosen_mesocycle"] = chosen_mesocycle
                else:
                    chosen_mesocycle = session.get("chosen_mesocycle")
            except KeyError as ke:
                chosen_mesocycle = None

            if chosen_mesocycle:
                table_population = tables_informations(chosen_mesocycle, dropdown_menu_info)
            else:
                table_population = {}
                       

    except TypeError:
        return render_template("table_layout.html", year=YEAR)
    
    if request.method == 'POST': # Check if a POST request was made
        if 'action' in request.form and request.form['action'] == 'export_excel':
            print("Export to Excel button was pressed!") # Debugging print
            excel_data_stream = workout_to_excel(table_population) 
            return send_file(
                excel_data_stream,  # This is the in-memory Excel file (BytesIO object)
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # Tells the browser it's an Excel .xlsx file
                as_attachment=True, # Forces the browser to download the file instead of trying to display it
                download_name='workout_plan.xlsx' # Sets the default filename for the downloaded file
            )



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

    if weekly is None and workout_names is None and workouts_id is None:
        return redirect("/home")

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
        if 'confirm_button' in request.form:
            add_session_to_db(workout_key, workout_id)
            submitted_data = request.form.to_dict()
            add_set_to_db(submitted_data, chosen_exercise, chosen_day)
            delete_set(submitted_data)
            # Get access to sets / exercises user want to change
            modify_set(submitted_data)

        elif 'repeat_button' in request.form:
            # If repeat button was clicked, last set will me "repeated"
            repeat_set(chosen_exercise, workout_id, chosen_day)

    sets_for_jinja = jinja_sets_function(chosen_day, chosen_exercise)

    # Reset placeholders to zero after the first set is saved
    if sets_for_jinja:
        exercise_placeholders = {'weight': 0, 'reps': 0, 'rpe': 0, 'notes': '...'}
    else:
        exercise_placeholders = current_exercise_info(chosen_exercise, chosen_day)

    preview = exercise_preview(workout_id, workout_key, chosen_exercise, workout_key, workout_id)
    sets_to_do_jinja = sets_to_do(chosen_exercise, chosen_day)
    
    # Data for preview
    last_exercise = last_exercise_preview(chosen_exercise, workout_id, chosen_day)

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
        placeholders=exercise_placeholders,
        last_exercise =last_exercise
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
    #session.pop("chosen_day", None) 
    chosen_day = "Choose Training Day"

    current_user_id = current_user_id_db()
    # Function to access workout day / data from database
    weekly, workout_names, workout_id = find_users_weeks()

    # Load amount of mesocycles
    all_users_mesocycles_query = db.session.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user_id
    )

    # Initialize variables
    chosen_mesocycle = session.get("chosen_mesocycle")
    if chosen_mesocycle is None:
        chosen_mesocycle = last_mesocycle_by_default()
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
    progress=exercise_progress,
)

@login_required
@app.route("/statistics", methods=["GET", "POST"])
def statistics():
    #graph_data = data_for_graph()
    used_exercises = all_exercises_list()
    graph = None

    if request.method == "POST":
        selected_value = request.form.get('chosen_exercise')
        exercise_data = statistics_for_exercise(selected_value)
        if exercise_data:
            graph = exercises_progress(exercise_data)

    return render_template("statistics.html",
                           graph = graph,
                           exercises = used_exercises
                           )

@login_required
@app.route("/intuitive_training", methods=["GET", "POST"])
def intuitive_training():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")
    DATE = NOW.strftime("%d%m%Y")
    
    selected_exercise = None
    exercise_name_for_last_sets = None
    sets_for_jinja = None
    last_day = None

    new_exercise = session.get("new_exercise", None)
    chosen_exercise_dropdown_i = session.get("chosen_exercise_by_user", None)

    # FIX: Consolidate the active exercise name into one variable immediately
    selected_exercise = new_exercise or chosen_exercise_dropdown_i
    exercise_name_for_last_sets = selected_exercise

    # Read data for current exercise 
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
        delete_set(submitted_data)
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
    
    # Check for last sets (FIXED: Use the unified selected_exercise)
    if selected_exercise:
        last_day = last_custom_day(selected_exercise)
        # exercise_name_for_last_sets is already set at the top, but you can set it here too
        exercise_name_for_last_sets = selected_exercise 

    if selected_exercise:
        sets_for_jinja = jinja_sets_function("c", selected_exercise)
        

    if not sets_for_jinja:
        sets_for_jinja = None
    
    # Reset placeholders to zero after the first set is saved
    if sets_for_jinja:
        exercise_placeholders = {'weight': 0, 'reps': 0, 'rpe': 0, 'notes': '...'}
    else:
        exercise_placeholders = current_exercise_info(selected_exercise, "c")
    return render_template(
        "intuitive_training.html",
        today=DATE,
        year=YEAR,
        today_session = today_session,
        saved_exercises = saved_exercises,
        selected_exercise = selected_exercise,
        sets_for_jinja = sets_for_jinja,
        placeholders= exercise_placeholders,
        preview = last_day,
        current_exercise_name = exercise_name_for_last_sets
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
    app.run(debug=True) # Delete this before pushing
