import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask,
    abort,
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
from wtforms.validators import DataRequired, EqualTo, NumberRange, ValidationError

from db_setup import db
from models.models import Users, WorkoutPlan, Mesocycles, load_user
from workout_management.workout_management import  WorkoutManagement

app = Flask(__name__, instance_relative_config=True)


def load_secret_key():
    """The session cookie is SIGNED with this key, so anyone who knows it can
    forge a cookie for any account - it must never sit in the repository.

    Order: an environment variable if one is set, otherwise a key file kept in
    instance/, which .gitignore already excludes. The file is generated on first
    run, so a fresh checkout or a fresh PythonAnywhere deploy just works and each
    environment ends up with its own key.
    """
    from_env = os.environ.get("WORKOUT_SECRET_KEY")
    if from_env:
        return from_env

    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "instance", "secret_key")
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as handle:
            key = handle.read().strip()
            if key:
                return key

    key = secrets.token_urlsafe(48)
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "w", encoding="utf-8") as handle:
        handle.write(key)
    try:
        os.chmod(key_path, 0o600)          # no-op on Windows, matters on the server
    except OSError:
        pass
    return key


app.secret_key = load_secret_key()

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

    # WTForms calls any validate_<field> method automatically, before
    # validate_on_submit() returns - so a taken name/email is rejected here,
    # as a normal form error, instead of reaching db.session.commit() and
    # blowing up with an IntegrityError from the users table's UNIQUE
    # constraint.
    def validate_username(self, field):
        if Users.query.filter_by(username=field.data).first():
            raise ValidationError("This username already exists.")

    def validate_email(self, field):
        if Users.query.filter_by(email=field.data).first():
            raise ValidationError("This email is already registered.")
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
reorder_exercises = db_operations.reorder_exercises
load_mesocycle_templates = db_operations.load_mesocycle_templates
apply_mesocycle_template = db_operations.apply_mesocycle_template
mesocycles_for_management = db_operations.mesocycles_for_management
delete_mesocycles = db_operations.delete_mesocycles
current_mesocycle_name = db_operations.current_mesocycle_name
rename_current_mesocycle = db_operations.rename_current_mesocycle
add_session_to_db = db_operations.add_session_to_db
find_exercise_id_db = db_operations.find_exercise_id_db
find_exercise_name_db = db_operations.find_exercise_name_db
add_set_to_db = db_operations.add_set_to_db
last_used_unit_for_exercise = db_operations.last_used_unit_for_exercise
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
progress_as_markdown = db_operations.progress_as_markdown
update_progress_entry = db_operations.update_progress_entry
fix_entry_unit = db_operations.fix_entry_unit
delete_progress_entry = db_operations.delete_progress_entry
fetch_exercise_suggestions = db_operations.fetch_exercise_suggestions
get_today_intuitive_traing = db_operations.get_today_intuitive_traing
create_custom_workout_exercise = db_operations.create_custom_workout_exercise
add_intuitive_exercise = db_operations.add_intuitive_exercise
check_c_session = db_operations.check_c_session
create_custom_workout_plan = db_operations.create_custom_workout_plan
load_custom_exercises_for_day = db_operations.load_custom_exercises_for_day
custom_session_exercises_overview = db_operations.custom_session_exercises_overview
exercise_progress_chart_data = db_operations.exercise_progress_chart_data
data_for_graph= db_operations.data_for_graph
statistics_for_exercise = db_operations.statistics_for_exercise
all_exercises_list = db_operations.all_exercises_list
exercises_ranked_by_use = db_operations.exercises_ranked_by_use
statistics_range_options = db_operations.statistics_range_options
statistics_range_label = db_operations.statistics_range_label
mesocycles_for_statistics = db_operations.mesocycles_for_statistics
exercises_for_mesocycle = db_operations.exercises_for_mesocycle
last_custom_day = db_operations.last_custom_day
workout_to_excel = db_operations.workout_to_excel
mesocycle_report_to_excel = db_operations.mesocycle_report_to_excel
last_mesocycle_by_default = db_operations.last_mesocycle_by_default
user_last_session_id = db_operations.user_last_session_id
suggest_training_focus = db_operations.suggest_training_focus
last_exercise_preview = db_operations.last_exercise_preview
arrow_buttons_next_exercise = db_operations.arrow_buttons_next_exercise
custom_session_dates = db_operations.custom_session_dates
custom_session_progress = db_operations.custom_session_progress

# Sentinel value for the "Custom Workouts" option in the /progress mesocycle
# dropdown - distinct from any real Mesocycles.name so a user's own mesocycle
# can never collide with it.
CUSTOM_WORKOUTS_OPTION = "__custom__"

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
        flash("Registration successful! An admin needs to approve your account "
              "before you can log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            if not user.is_approved:
                flash("Your account is waiting on admin approval - try again "
                      "later.", "warning")
                return render_template("login.html", form=form,
                                        next=request.args.get("next"))
            login_user(user)

            next_page = request.args.get("next") or request.form.get("next")

            # Fix: ignore invalid values
            if next_page and next_page != "None":
                return redirect(next_page)

            return redirect(url_for("profile"))

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

        # What was actually lifted this mesocycle, as opposed to the plan above
        elif request.form.get('action') == 'mesocycle_report':
            report = mesocycle_report_to_excel(chosen_mesocycle, dropdown_menu_info)

            if report is None:
                flash("No sets logged in this mesocycle yet - nothing to report.", "warning")
                return redirect(url_for("workout_plan_page"))

            # All lower case, and no runs of underscores where the name had
            # spaces or punctuation: "Strenght & Regeneration" would otherwise
            # land as ..._Strenght___Regeneration.xlsx.
            safe_name = "".join(
                c if c.isalnum() or c in "-_" else "_"
                for c in str(chosen_mesocycle or "mesocycle").lower()
            )
            while "__" in safe_name:
                safe_name = safe_name.replace("__", "_")
            safe_name = safe_name.strip("_") or "mesocycle"
            return send_file(
                report,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f"mesocycle_report_{safe_name}.xlsx"
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
        # The template picker: build the whole mesocycle and go straight to it.
        if request.form.get("action") == "use_template":
            created = apply_mesocycle_template(request.form.get("template_id"))
            if not created:
                flash("That template could not be loaded.", "warning")
                return redirect(url_for("table_layout"))

            flash(f"Created \"{created}\" - edit it below.", "success")
            return redirect(url_for("create_workout"))

        meso_name = request.form.get("meso_name")
        meso_duration = request.form.get("mesocycle")
        # "Workouts Per Week" is no longer asked for. Four days is the default
        # for a from-scratch plan; the column still has to match the number of
        # WorkoutPlan rows created below, because find_users_weeks() limits by
        # it and create_workout() walks range() over the result.
        workouts_per_week = 4

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
            
    return render_template(
        "table_layout.html", year=YEAR, templates=load_mesocycle_templates()
    )

# ----------------------------------------------------------------------
# The only page that can destroy a plan. Tick, press Delete, confirm.
#
# A delete removes the mesocycle, its workout days and their exercises. Every
# session and every logged set stays in the database - /statistics still draws
# that training. See delete_mesocycles() for the full list.
@app.route("/mesocycle_management", methods=["GET", "POST"])
@login_required
def mesocycle_management():
    NOW = datetime.now()
    YEAR = NOW.strftime("%Y")

    if request.method == "POST" and request.form.get("action") == "delete":
        # getlist, not get: one name carries every ticked box.
        chosen = request.form.getlist("mesocycle_id")
        if not chosen:
            flash("Nothing was ticked, so nothing was deleted.", "warning")
            return redirect(url_for("mesocycle_management"))

        deleted = delete_mesocycles(chosen)

        if not deleted:
            flash("Nothing was deleted.", "warning")
        else:
            # /workout_plan_page and /progress remember a mesocycle by NAME in
            # the cookie session. Left pointing at a deleted one they render an
            # empty plan with no explanation.
            if session.get("chosen_mesocycle") in deleted:
                session.pop("chosen_mesocycle", None)
                session.pop("chosen_day", None)
                session.pop("training_day", None)

            names = ", ".join(f'"{name}"' for name in deleted)
            flash(f"Deleted {names}. Your logged training was kept.", "success")

        return redirect(url_for("mesocycle_management"))

    return render_template(
        "mesocycle_management.html",
        year=YEAR,
        mesocycles=mesocycles_for_management(),
    )

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

        # Renaming the mesocycle is its own little form at the top of the page,
        # nothing to do with the plan below it. Handled first and returned from,
        # so a rename never runs the exercise save with an empty form.
        if submitted_data.get("action") == "rename_mesocycle":
            ok, old_name, message = rename_current_mesocycle(
                submitted_data.get("mesocycle_name")
            )
            if not ok:
                flash(message or "That name could not be saved.", "warning")
            else:
                new_name = (submitted_data.get("mesocycle_name") or "").strip()[:100]
                if new_name != old_name:
                    # The cookie remembers a mesocycle by name, not by id.
                    if session.get("chosen_mesocycle") == old_name:
                        session["chosen_mesocycle"] = new_name
                    flash(f'Renamed to "{new_name}".', "success")
            return redirect(url_for("create_workout"))

        # Name of workout is default set 1-x and user can change it
        workout_names = find_workout_name_from_user(submitted_data, weekly, workout_names)

        # Save new exercise into database - return order number
        exercises_dict = add_exercise(submitted_data, order, weekly, jinja_exercises, workouts_id)

        # Call function to delete exercise from workout
        delete_exercise(submitted_data, workouts_id)

        # Apply the order the user dragged the rows into. Before
        # overwrite_exercise so the rest of the save sees final positions.
        reorder_exercises(submitted_data, weekly, workouts_id)

        # Call function to overwrite exercise
        overwrite_exercise(submitted_data, workouts_id)

        # Use the PRG pattern: Redirect to prevent resubmission.
        #
        # "next" is set only by the unsaved-changes dialog, so that saving on
        # the way out lands you where you were going. Anything but a plain
        # same-site path is ignored: a leading "//" or "/\\" is read by
        # browsers as another origin, which would make this an open redirect.
        next_url = (submitted_data.get("next") or "").strip()
        if (
            next_url.startswith("/")
            and not next_url.startswith("//")
            and not next_url.startswith("/\\")
        ):
            return redirect(next_url)

        return redirect(url_for("create_workout"))

    return render_template(
        "create_workout.html",
        week=weekly,
        w_names=workout_names,
        exe_order=order,
        user_exe=jinja_exercises,
        mesocycle_name=current_mesocycle_name(),
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

    load_workout_day = request.args.get("training_day")

    # The browser session dies fairly often on a phone. When it does, re-pick
    # the day and exercise from the database rather than showing empty
    # dropdowns: today's workout if one is already in progress, otherwise the
    # next day in the rotation. Skipped when the user is actively changing the
    # dropdown this request, so an explicit blank choice is not fought.
    if not chosen_day and load_workout_day is None:
        suggested_day, suggested_exercise = suggest_training_focus()

        if suggested_day:
            chosen_day = suggested_day
            session["chosen_day"] = suggested_day

            if suggested_exercise and not chosen_exercise:
                chosen_exercise = suggested_exercise
                session["chosen_exercise"] = suggested_exercise

    # Create list of exercises -> for jinja purposes
    workout_key = next((k for k, v in workouts_id_name.items() if v == chosen_day), 0)

    exercises_from_user: dict = jinja_exercises[workout_key]
    exercises_in_workout: list = [x["exercise"] for x in exercises_from_user]

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
            # request.form (not submitted_data) - delete_set needs every
            # checked "delete" checkbox, and .to_dict() only kept the first.
            delete_set(request.form)
            # Get access to sets / exercises user want to change
            modify_set(submitted_data)
        elif 'previous_day' in request.form:
            # arrow_buttons_next_exercise
            # Sore exercise in session
            previous_exercise = arrow_buttons_next_exercise("previous_day", chosen_exercise, chosen_day)
            if previous_exercise:
                session["chosen_exercise"] = previous_exercise
                return redirect(url_for("training_session"))
        elif 'next_day' in request.form:
            # arrow_buttons_next_exercise
            next_exercise = arrow_buttons_next_exercise("next_day", chosen_exercise, chosen_day)
            if next_exercise:
                session["chosen_exercise"] = next_exercise
                return redirect(url_for("training_session"))
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

    # Kg/Lbs/Other toggle above the weight column - defaults to whatever unit
    # this exercise was last logged in.
    default_unit = last_used_unit_for_exercise(chosen_exercise)

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
        last_exercise =last_exercise,
        default_unit=default_unit,
    )

# --------------------------------------------------------------------------
@app.route("/execute_workout_plan_exercises")
@login_required
def execute_workout_plan_exercises():
    return render_template("<h1>Just test if process will pass<h1>")
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
#  Admin: signing in as another user
#
#  The whole feature rests on two rules:
#    1. Whether you are an admin is read from the DATABASE on every request,
#       never from anything the browser sent.
#    2. Who you really are while impersonating lives in session["impersonator_id"],
#       inside the signed session cookie - which is why the signing key must
#       stay out of the repository (see load_secret_key above).
# --------------------------------------------------------------------------

IMPERSONATOR_KEY = "impersonator_id"


def admin_required(view):
    """404 rather than 403 for non-admins - no reason to advertise the route."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(404)
        return view(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_impersonation():
    """Every template can ask whether this session is impersonating, and who
    the real admin is, so the banner can render on any page."""
    impersonator = None
    impersonator_id = session.get(IMPERSONATOR_KEY)
    if impersonator_id:
        impersonator = db.session.get(Users, impersonator_id)
    return {"impersonator": impersonator}


@app.route("/admin/impersonate", methods=["POST"])
@login_required
@admin_required
def impersonate():
    if session.get(IMPERSONATOR_KEY):
        abort(400)                                  # already impersonating, no nesting

    try:
        target_id = int(request.form.get("user_id", ""))
    except (TypeError, ValueError):
        abort(400)

    target = db.session.get(Users, target_id)
    if target is None:
        abort(404)
    if target.user_id == current_user.user_id:
        abort(400)
    if target.is_admin:
        abort(403)                                  # admins are never a target

    admin_id = current_user.user_id

    # The session carries chosen_day / chosen_exercise / chosen_mesocycle, and
    # those decide where a confirmed set gets written. Carrying them into
    # someone else's account would log sets into the wrong diary, so the whole
    # session goes. Clear first, log in second, stamp the key last.
    logout_user()
    session.clear()
    login_user(target)
    session[IMPERSONATOR_KEY] = admin_id

    flash(f"You are now signed in as {target.username}.", "info")
    return redirect(url_for("profile"))


@app.route("/admin/stop-impersonating", methods=["POST"])
@login_required
def stop_impersonating():
    admin_id = session.get(IMPERSONATOR_KEY)
    if not admin_id:
        abort(404)

    admin = db.session.get(Users, admin_id)
    # Re-check the role against the database. Even if this key were somehow
    # planted, it would have to name a real admin to get anywhere.
    if admin is None or not admin.is_admin:
        logout_user()
        session.clear()
        abort(403)

    logout_user()
    session.clear()
    login_user(admin)

    flash("Back on your own account.", "success")
    return redirect(url_for("profile"))


@app.route("/admin/approve_user", methods=["POST"])
@login_required
@admin_required
def approve_user():
    try:
        target_id = int(request.form.get("user_id", ""))
    except (TypeError, ValueError):
        abort(400)

    target = db.session.get(Users, target_id)
    if target is None:
        abort(404)

    target.is_approved = True
    db.session.commit()

    flash(f"{target.username} can now log in.", "success")
    return redirect(url_for("profile"))


@app.route("/admin/decline_user", methods=["POST"])
@login_required
@admin_required
def decline_user():
    """Reject a pending registration by deleting the account outright - it
    never logged in (is_approved gates that), so there is no training data
    of theirs to lose."""
    try:
        target_id = int(request.form.get("user_id", ""))
    except (TypeError, ValueError):
        abort(400)

    target = db.session.get(Users, target_id)
    if target is None:
        abort(404)
    # Only ever a still-pending signup - never a live account, admin or not.
    if target.is_approved:
        abort(400)

    username = target.username
    db.session.delete(target)
    db.session.commit()

    flash(f"Declined and removed {username}.", "success")
    return redirect(url_for("profile"))


MIN_PASSWORD_LENGTH = 8


@app.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    """Change the password of whoever is currently signed in.

    While impersonating, that is the friend whose account you are in - so this
    doubles as the admin reset tool. In that case the password you must type to
    prove yourself is YOUR OWN admin password, because you do not know theirs.
    """
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    repeat = request.form.get("repeat_password", "")

    impersonator_id = session.get(IMPERSONATOR_KEY)
    if impersonator_id:
        verifier = db.session.get(Users, impersonator_id)
        # Same re-check as the return route: trust the database, not the cookie.
        if verifier is None or not verifier.is_admin:
            logout_user()
            session.clear()
            abort(403)
    else:
        verifier = current_user

    if not check_password_hash(verifier.password, current):
        flash("That password is not right, nothing was changed.", "error")
        return redirect(url_for("profile"))

    if len(new) < MIN_PASSWORD_LENGTH:
        flash(f"The new password needs at least {MIN_PASSWORD_LENGTH} characters.", "error")
        return redirect(url_for("profile"))

    if new != repeat:
        flash("The two new passwords do not match.", "error")
        return redirect(url_for("profile"))

    target = db.session.get(Users, current_user.user_id)
    target.password = generate_password_hash(new, method="pbkdf2:sha256")
    db.session.commit()

    if impersonator_id:
        flash(f"Password changed for {target.username}. Tell them what it is.", "success")
    else:
        flash("Your password has been changed.", "success")
    return redirect(url_for("profile"))


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
    elif action == 'mesocycle_management':
        # Handle deleting old mesocycles
        return redirect(url_for("mesocycle_management"))

    users_to_impersonate = []
    pending_users = []
    if current_user.is_admin and not session.get(IMPERSONATOR_KEY):
        # Never offer yourself, and never offer another admin.
        users_to_impersonate = (
            db.session.query(Users)
            .filter(Users.user_id != current_user.user_id)
            .filter(Users.role != "admin")
            .order_by(Users.username)
            .all()
        )
        pending_users = (
            db.session.query(Users)
            .filter(Users.is_approved.is_(False))
            .order_by(Users.username)
            .all()
        )

    return render_template(
        "profile.html",
        users_to_impersonate=users_to_impersonate,
        pending_users=pending_users,
    )

# --------------------------------------------------------------------------
@app.route("/progress", methods=["GET", "POST"])
@login_required
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
    custom_dates = []
    chosen_custom_session_id = session.get("chosen_custom_session_id")

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
                # A different mesocycle invalidates whatever day/date was
                # picked under the old one - "Custom Workouts" for mesocycle A
                # is not the same list as for mesocycle B.
                session.pop("chosen_day", None)
                session.pop("chosen_exercise", None)
                session.pop("chosen_custom_session_id", None)
            else:
                # If no mesocycle selected, remove from session
                session.pop("chosen_mesocycle", None)
                session.pop("training_day", None)
                chosen_mesocycle = None

        # Ensure `chosen_mesocycle` is set before generating `workout_day_info`
        if chosen_mesocycle:
            workout_day_info = workout_day_information(chosen_mesocycle, dropdown_menu_info)
            custom_dates = custom_session_dates(chosen_mesocycle, dropdown_menu_info)
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
    exercises_in_workout = [x["exercise"] for x in exercises_from_user]

    # Handle GET parameters
    if request.method == "GET":
        load_workout_day = request.args.get("training_day")
        if load_workout_day is not None:
            if load_workout_day == "":
                session.pop("chosen_day", None)
                chosen_day = None
            else:
                # "Custom Workouts" is just another option in this same
                # dropdown - it is not a real training day, but it is picked
                # the same way, and switching to/from it invalidates whatever
                # was chosen one level down just like switching days does.
                session["chosen_day"] = load_workout_day
                chosen_day = load_workout_day
                session.pop("chosen_exercise", None)
                chosen_exercise = None
                session.pop("chosen_custom_session_id", None)
                return redirect(url_for("progress"))

        load_chosen_exercise = request.args.get("chosen_exercise")
        if load_chosen_exercise is not None:
            if load_chosen_exercise == "":
                session.pop("chosen_exercise", None)
                chosen_exercise = None
            else:
                session["chosen_exercise"] = load_chosen_exercise
                chosen_exercise = load_chosen_exercise

        load_custom_date = request.args.get("custom_date")
        if load_custom_date is not None:
            if load_custom_date == "":
                session.pop("chosen_custom_session_id", None)
                chosen_custom_session_id = None
            else:
                try:
                    chosen_custom_session_id = int(load_custom_date)
                except ValueError:
                    chosen_custom_session_id = None
                session["chosen_custom_session_id"] = chosen_custom_session_id

        if chosen_day == CUSTOM_WORKOUTS_OPTION:
            # Nothing picked yet - default to the most recent freestyle
            # session, same "open the latest one" behaviour as the arrows.
            if chosen_custom_session_id is None and custom_dates:
                chosen_custom_session_id = custom_dates[0]["session_id"]
            exercise_progress = custom_session_progress(chosen_custom_session_id)
        elif workout_day_info:
            exercise_progress = exercise_progress_data(workout_day_info, chosen_day, chosen_mesocycle)

    # Human-readable title bits for the copy-to-markdown button.
    if chosen_day == CUSTOM_WORKOUTS_OPTION:
        chosen_custom_date_label = next(
            (d["label"] for d in custom_dates if d["session_id"] == chosen_custom_session_id),
            None,
        )
        copy_text = progress_as_markdown(exercise_progress, chosen_custom_date_label, chosen_mesocycle)
    else:
        copy_text = progress_as_markdown(exercise_progress, chosen_day, chosen_mesocycle)

    return render_template(
    "progress.html",
    today=DATE,
    year=YEAR,
    w_names=workouts_id_name,
    chosen_day=chosen_day,
    dropdown=dropdown_menu_info,
    chosen_mesocycle=chosen_mesocycle,
    custom_sentinel=CUSTOM_WORKOUTS_OPTION,
    custom_dates=custom_dates,
    chosen_custom_session_id=chosen_custom_session_id,
    workouts_info=workout_day_info,
    progress=exercise_progress,
    copy_text=copy_text,
)

@app.route("/progress/update_entry", methods=["POST"])
@login_required
def progress_update_entry():
    payload = request.get_json(silent=True) or {}
    entry_id = payload.get("entry_id")
    if not entry_id:
        return jsonify({"ok": False, "error": "Missing entry_id."}), 400

    result = update_progress_entry(
        entry_id=entry_id,
        reps=payload.get("reps"),
        weight=payload.get("weight"),
        rpe=payload.get("rpe"),
        notes=payload.get("notes"),
    )
    return jsonify(result), (200 if result.get("ok") else 400)

@app.route("/progress/fix_unit", methods=["POST"])
@login_required
def progress_fix_unit():
    payload = request.get_json(silent=True) or {}
    entry_id = payload.get("entry_id")
    if not entry_id:
        return jsonify({"ok": False, "error": "Missing entry_id."}), 400

    result = fix_entry_unit(
        entry_id=entry_id,
        target_unit=payload.get("unit"),
        scope=payload.get("scope"),
    )
    return jsonify(result), (200 if result.get("ok") else 400)

@app.route("/progress/delete_entry", methods=["POST"])
@login_required
def progress_delete_entry():
    payload = request.get_json(silent=True) or {}
    entry_id = payload.get("entry_id")
    if not entry_id:
        return jsonify({"ok": False, "error": "Missing entry_id."}), 400

    result = delete_progress_entry(entry_id=entry_id)
    return jsonify(result), (200 if result.get("ok") else 400)

@app.route("/statistics", methods=["GET"])
@login_required
def statistics():
    # Bare landing page - just "Mesocycle period" / "Time period", no
    # picker, no chart. The data is a mess across a year-plus of logging, so
    # this exists purely to make you commit to one lens before anything
    # else renders, rather than presenting both scopes tangled together.
    YEAR = datetime.now().strftime("%Y")
    return render_template("statistics.html", year=YEAR)

@app.route("/period_statistics", methods=["GET", "POST"])
@login_required
def period_statistics():
    """"Time period" lens: the original /statistics picker - search an
    exercise, pick a preset time window, see the chart. No mesocycle
    scoping here at all; that lives entirely on /mesocycle_statistics now.
    """
    YEAR = datetime.now().strftime("%Y")
    # Most-used first; the picker shows the top 10 and hides the rest behind
    # "show more", but searches the whole list as soon as you type.
    used_exercises = exercises_ranked_by_use()
    graph_data = None
    selected_value = None
    chosen_period = db_operations.DEFAULT_STATISTICS_RANGE
    no_data_in_period = False

    if request.method == "POST":
        selected_value = request.form.get('chosen_exercise')
        chosen_period = request.form.get('period') or db_operations.DEFAULT_STATISTICS_RANGE
        exercise_data = statistics_for_exercise(selected_value, chosen_period)
        if exercise_data:
            graph_data = exercise_progress_chart_data(
                exercise_data, statistics_range_label(chosen_period)
            )
        elif selected_value:
            # Exercise is valid but has nothing inside the chosen window - say
            # so, rather than rendering a blank space.
            no_data_in_period = True

    return render_template("period_statistics.html",
                           year = YEAR,
                           graph_data = graph_data,
                           exercises = used_exercises,
                           chosen_exercise = selected_value,
                           periods = statistics_range_options(),
                           chosen_period = chosen_period,
                           no_data_in_period = no_data_in_period
                           )

@app.route("/mesocycle_statistics", methods=["GET", "POST"])
@login_required
def mesocycle_statistics():
    """"Mesocycle period" lens: pick a mesocycle from a popup (not a
    dropdown - the mesocycle list itself never changes mid-session, so there
    is nothing to search/filter, just a short list to tap), then an exercise
    from a plain dropdown of what was actually logged in it, then the chart.

    The two picks are remembered in the session so paging around (or
    picking a different exercise in the same mesocycle) does not force you
    back through the popup every time - "change_mesocycle" is the explicit
    way out of that.
    """
    YEAR = datetime.now().strftime("%Y")
    mesocycles = mesocycles_for_statistics()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "choose_mesocycle":
            session["stats_mesocycle_id"] = request.form.get("mesocycle_id")
            session.pop("stats_mesocycle_exercise", None)
        elif action == "change_mesocycle":
            session.pop("stats_mesocycle_id", None)
            session.pop("stats_mesocycle_exercise", None)
        elif action == "choose_exercise":
            session["stats_mesocycle_exercise"] = request.form.get("chosen_exercise")
        return redirect(url_for("mesocycle_statistics"))

    chosen_mesocycle_id = session.get("stats_mesocycle_id")
    chosen_mesocycle = next(
        (m for m in mesocycles if str(m["mesocycle_id"]) == str(chosen_mesocycle_id)),
        None,
    )

    exercises_in_mesocycle = []
    chosen_exercise = None
    graph_data = None
    no_data_in_period = False

    if chosen_mesocycle:
        exercises_in_mesocycle = exercises_for_mesocycle(chosen_mesocycle["mesocycle_id"])
        chosen_exercise = session.get("stats_mesocycle_exercise")
        all_exercise_names = [
            name for group in exercises_in_mesocycle for name in group["exercises"]
        ]

        if chosen_exercise and chosen_exercise in all_exercise_names:
            exercise_data = statistics_for_exercise(
                chosen_exercise, mesocycle_id=chosen_mesocycle["mesocycle_id"]
            )
            if exercise_data:
                graph_data = exercise_progress_chart_data(exercise_data, chosen_mesocycle["name"])
            else:
                no_data_in_period = True
        else:
            # Stale/invalid pick (e.g. from before a different mesocycle was
            # chosen) - drop it rather than rendering a mismatched chart.
            chosen_exercise = None
            session.pop("stats_mesocycle_exercise", None)

    return render_template("mesocycle_statistics.html",
                           year = YEAR,
                           mesocycles = mesocycles,
                           chosen_mesocycle = chosen_mesocycle,
                           exercises_in_mesocycle = exercises_in_mesocycle,
                           chosen_exercise = chosen_exercise,
                           graph_data = graph_data,
                           no_data_in_period = no_data_in_period
                           )

@app.route("/intuitive_training", methods=["GET", "POST"])
@login_required
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

    # The exercise-selection cookie has no idea what day it is - it happily
    # carries "Barbell Bench Press" over from three days ago into a brand
    # new freestyle session. saved_exercises, by contrast, is read fresh
    # from the DB every request and is already scoped to TODAY's plan (see
    # load_custom_exercises_for_day). So trust the DB, not the cookie: a
    # selection that isn't actually part of today's plan is stale and gets
    # dropped, rather than displayed as if it were today's choice.
    if selected_exercise and selected_exercise not in saved_exercises:
        selected_exercise = None
        exercise_name_for_last_sets = None
        session.pop("chosen_exercise_by_user", None)
        session.pop("new_exercise", None)

    if request.method == "GET":
        # Check existance of the today's custom workout 
        user_confirm = request.args.get("confirm_freestyle")

        if user_confirm:
            # Create today's freestyle plan. The Session itself is created
            # lazily, on the first logged set (see add_set_to_db), so
            # confirming freestyle without ever logging anything leaves no
            # trace behind.
            try_to_create_custom_w_plan = create_custom_workout_plan()
            if try_to_create_custom_w_plan:
                return redirect(url_for('intuitive_training'))
        else:
            print('No confirmation yet')
            
        # Check if there are already some exercies in workout - In case website / webbrowser would crash and we had no POST after opening :)
        search_term = request.args.get("query")
        if search_term:
            exercise_names = fetch_exercise_suggestions(search_term)
            return jsonify(exercise_names)
        
    else:  # POST
        submitted_data = request.form.to_dict()
        # request.form (not submitted_data) - delete_set needs every checked
        # "delete" checkbox, and .to_dict() only kept the first.
        delete_set(request.form)

        if "previous_day" in submitted_data or "next_day" in submitted_data:
            move = "previous_day" if "previous_day" in submitted_data else "next_day"
            target_exercise = arrow_buttons_next_exercise(move, selected_exercise, "c")
            if target_exercise:
                session["chosen_exercise_by_user"] = target_exercise
                session.pop("new_exercise", None)
            return redirect(url_for("intuitive_training"))

        action = submitted_data.get("action")

        if action == "choose_exercise":
            chosen_exercise = submitted_data.get("chosen_exercise")
            if chosen_exercise:
                session["chosen_exercise_by_user"] = chosen_exercise
                session.pop("new_exercise", None)
                return redirect(url_for("intuitive_training"))

        else:
            # Same shared form also carries the "add a new exercise" text
            # box. Registering it must NOT short-circuit past the reps
            # below - the natural flow is search, click a suggestion, type
            # today's weight/reps, then hit Confirm once.
            new_exercise = submitted_data.get("exercise")

            if new_exercise:
               create_custom_workout_exercise(new_exercise)
               session["new_exercise"] = new_exercise
               session.pop("chosen_exercise_by_user", None)
               selected_exercise = new_exercise

            if submitted_data.get("reps"):
                add_set_to_db(submitted_data, selected_exercise, "c")

            return redirect(url_for("intuitive_training"))
    
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

    exercises_overview = custom_session_exercises_overview() if today_session else []

    # Kg/Lbs/Other toggle above the weight column - defaults to whatever unit
    # this exercise was last logged in.
    default_unit = last_used_unit_for_exercise(selected_exercise)

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
        current_exercise_name = exercise_name_for_last_sets,
        exercises_overview = exercises_overview,
        default_unit = default_unit,
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
