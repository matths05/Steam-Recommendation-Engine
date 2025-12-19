from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from .forms import PreferencesForm

profile = Blueprint("profile", __name__, url_prefix="/profile")

@profile.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    form = PreferencesForm()

    # Pre-fill current values on GET
    if form.favorite_tags.data is None or form.hated_tags.data is None:
        form.favorite_tags.data = current_user.favorite_tags
        form.hated_tags.data = current_user.hated_tags

    if form.validate_on_submit():
        current_user.favorite_tags = form.favorite_tags.data
        current_user.hated_tags = form.hated_tags.data
        current_user.save()
        return redirect(url_for("profile.preferences"))

    return render_template("preferences.html", form=form)
