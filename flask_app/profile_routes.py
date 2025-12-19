from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .forms import PreferencesForm, FriendCompareForm, SteamIdForm, SyncSteamForm
from datetime import datetime
from .steam_api import get_owned_games, resolve_to_steamid64

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

@profile.route("/steam", methods=["GET", "POST"])
@login_required
def steam_settings():
    steam_form = SteamIdForm(prefix="steam")
    sync_form = SyncSteamForm(prefix="sync")

    # Pre-fill steam_id
    if not steam_form.is_submitted():
        steam_form.steam_id.data = current_user.steam_id or ""

    if steam_form.validate_on_submit() and steam_form.submit.data:
        current_user.steam_id = steam_form.steam_id.data.strip()
        current_user.save()
        return redirect(url_for("profile.steam_settings"))

    if sync_form.validate_on_submit() and sync_form.submit.data:
        if not current_user.steam_id:
            return redirect(url_for("profile.steam_settings"))

        try:
            steamid64 = resolve_to_steamid64(current_user.steam_id)
            games = get_owned_games(steamid64)
        except Exception:
            # Keep it simple (no flash). Just don't sync if invalid.
            return redirect(url_for("profile.steam_settings"))

        current_user.steam_id = steamid64  # normalize stored ID to SteamID64
        current_user.owned_games = [
            {
                "appid": g.get("appid"),
                "name": g.get("name"),
                "playtime_forever": g.get("playtime_forever", 0),
            }
            for g in games
            if g.get("appid") is not None
        ]
        current_user.last_sync = datetime.utcnow()
        current_user.save()

        return redirect(url_for("profile.steam_settings"))

    owned = current_user.owned_games or []
    top_games = sorted(
        owned,
        key=lambda x: x.get("playtime_forever", 0),
        reverse=True
    )[:10]

    return render_template(
        "steam.html",
        steam_form=steam_form,
        sync_form=sync_form,
        owned_count=len(owned),
        last_sync=current_user.last_sync,
        top_games=top_games,
    )

