from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    mesocycles = db.relationship('Mesocycle', backref='user', lazy=True)
    workouts = db.relationship('Workout', backref='user', lazy=True)
    sessions = db.relationship('Session', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Exercise(db.Model):
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    muscle_group = db.Column(db.String(100))
    description = db.Column(db.Text)

    workout_exercises = db.relationship('WorkoutExercise', backref='exercise', lazy=True)
    exercise_entries = db.relationship('ExerciseEntry', backref='exercise', lazy=True)

    def __repr__(self):
        return f'<Exercise {self.exercise_name}>'


class Workout(db.Model):
    __tablename__ = 'workouts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workout_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

    workout_exercises = db.relationship('WorkoutExercise', backref='workout', lazy=True)
    sessions = db.relationship('Session', backref='workout', lazy=True)

    def __repr__(self):
        return f'<Workout {self.workout_name}>'


class WorkoutExercise(db.Model):
    __tablename__ = 'workout_exercises'

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    order_in_workout = db.Column(db.Integer)
    prescribed_sets = db.Column(db.Integer)
    prescribed_reps = db.Column(db.Integer)
    prescribed_weight = db.Column(db.Float)
    rest_period = db.Column(db.Integer)

    def __repr__(self):
        return f'<WorkoutExercise WorkoutID:{self.workout_id} ExerciseID:{self.exercise_id}>'


class Session(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    exercise_entries = db.relationship('ExerciseEntry', backref='session', lazy=True)
    session_mesocycle = db.relationship('SessionMesocycle', backref='session', uselist=False)

    def __repr__(self):
        return f'<Session ID:{self.id} UserID:{self.user_id}>'


class ExerciseEntry(db.Model):
    __tablename__ = 'exercise_entries'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    set_number = db.Column(db.Integer)
    actual_reps = db.Column(db.Integer)
    actual_weight = db.Column(db.Float)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<ExerciseEntry SessionID:{self.session_id} ExerciseID:{self.exercise_id}>'


class Mesocycle(db.Model):
    __tablename__ = 'mesocycles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    session_mesocycles = db.relationship('SessionMesocycle', backref='mesocycle', lazy=True)

    def __repr__(self):
        return f'<Mesocycle {self.name}>'


class SessionMesocycle(db.Model):
    __tablename__ = 'session_mesocycles'

    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), primary_key=True)
    mesocycle_id = db.Column(db.Integer, db.ForeignKey('mesocycles.id'), primary_key=True)
    training_day_number = db.Column(db.Integer)

    def __repr__(self):
        return f'<SessionMesocycle SessionID:{self.session_id} MesocycleID:{self.mesocycle_id}>'
