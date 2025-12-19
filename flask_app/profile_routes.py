from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .forms import PreferencesForm, FriendCompareForm


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

@profile.route("/friend-compare", methods=["GET", "POST"])
@login_required
def friend_compare():
    form = FriendCompareForm()

    # Pre-fill with saved value on GET
    if not form.is_submitted():
        form.friend_steam_id.data = current_user.friend_steam_id or ""

    if form.validate_on_submit():
        current_user.friend_steam_id = form.friend_steam_id.data.strip()
        current_user.save()
        return redirect(url_for("profile.friend_compare"))

    return render_template("friend_compare.html", form=form)
