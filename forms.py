from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, IntegerField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class RaceForm(FlaskForm):
    name = StringField('Race Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    location = StringField('Location')
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[Optional()])
    distance = FloatField('Distance (km)', validators=[Optional()])
    max_participants = IntegerField('Maximum Participants', validators=[Optional()])
    is_active = BooleanField('Active')
    submit = SubmitField('Save Race')

class RaceEntryForm(FlaskForm):
    agree_to_terms = BooleanField('I agree to the race terms and conditions', validators=[DataRequired()])
    submit = SubmitField('Register for Race')