from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    IntegerField,
    FloatField,
    SubmitField,
    SelectField,
    TextAreaField,
    DateField,
)
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(
        'Password', validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')]
    )
    confirm = PasswordField('Confirm Password')
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class CreateWorkoutForm(FlaskForm):
    workout_name = StringField('Workout Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Workout')


class AddExercisesForm(FlaskForm):
    exercise = SelectField('Exercise', coerce=int, choices=[], validators=[DataRequired()])
    prescribed_sets = IntegerField('Sets', validators=[DataRequired(), NumberRange(min=1)])
    prescribed_reps = IntegerField('Reps', validators=[DataRequired(), NumberRange(min=1)])
    prescribed_weight = FloatField('Weight', validators=[DataRequired(), NumberRange(min=0)])
    rest_period = IntegerField('Rest Period (sec)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Exercise')


class CreateExerciseForm(FlaskForm):
    exercise_name = StringField('Exercise Name', validators=[DataRequired()])
    muscle_group = StringField('Muscle Group')
    description = TextAreaField('Description')
    submit = SubmitField('Create Exercise')


class LogSessionForm(FlaskForm):
    notes = TextAreaField('Session Notes')
    submit = SubmitField('Log Session')


class CreateMesocycleForm(FlaskForm):
    name = StringField('Mesocycle Name', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d')
    end_date = DateField('End Date', format='%Y-%m-%d')
    submit = SubmitField('Create Mesocycle')
