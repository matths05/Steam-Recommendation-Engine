from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

from .forms import RegisterForm, LoginForm
from .models import User

auth = Blueprint("auth", __name__, url_prefix="/auth")
bcrypt = Bcrypt()

@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.objects(email=form.email.data.lower()).first()
        if existing:
            flash("That email is already registered.", "error")
            return redirect(url_for("auth.register"))

        pw_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        User(email=form.email.data.lower(), password_hash=pw_hash).save()

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data.lower()).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash("Logged in!", "success")
            return redirect(url_for("main.home"))

        flash("Invalid email or password.", "error")

    return render_template("login.html", form=form)

@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))

