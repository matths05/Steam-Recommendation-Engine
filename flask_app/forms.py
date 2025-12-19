from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


TAG_CHOICES = [
    ("Action", "Action"),
    ("Adventure", "Adventure"),
    ("RPG", "RPG"),
    ("Strategy", "Strategy"),
    ("Simulation", "Simulation"),
    ("Puzzle", "Puzzle"),
    ("Horror", "Horror"),
    ("Sports", "Sports"),
]

class PreferencesForm(FlaskForm):
    favorite_tags = SelectMultipleField("Favorite Tags", choices=TAG_CHOICES, validators=[Optional()])
    hated_tags = SelectMultipleField("Hated Tags", choices=TAG_CHOICES, validators=[Optional()])
    submit = SubmitField("Save Preferences")

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

class FriendCompareForm(FlaskForm):
    friend_steam_id = StringField(
        "Friend Steam ID",
        validators=[DataRequired(), Length(min=3, max=32)]
    )
    submit = SubmitField("Save Friend ID")

