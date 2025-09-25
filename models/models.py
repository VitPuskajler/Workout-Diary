from db_setup import db
from flask_login import UserMixin
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    DateTime,
    func,
    select,
)

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
# 4. WorkoutExercises Table
class WorkoutExercises(UserMixin, db.Model):
    __tablename__ = "workout_exercises"
    workout_exercise_id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    exercise_id = Column(Integer, db.ForeignKey("exercises.exercise_id"))
    order_in_workout = Column(Integer, unique=False, nullable=False)
    prescribed_sets = Column(Integer, unique=False, nullable=False)
    rest_period = Column(Integer, unique=False, nullable=False)

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
# 5. Sessions Table
class Sessions(UserMixin, db.Model):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey("users.user_id"))
    workout_id = Column(Integer, db.ForeignKey("workouts.workout_id"))
    session_date = Column(DateTime, default=func.now())
    notes = Column(String(150), unique=False, nullable=True)
    session_end = Column(DateTime, unique=True, nullable=True)

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

# User Loader function (belongs with the Users model)
def load_user(user_id):
    stmt = select(Users).where(Users.user_id == int(user_id))
    return db.session.execute(stmt).scalar_one_or_none()