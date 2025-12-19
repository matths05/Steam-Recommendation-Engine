import re
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .forms import PreferencesForm, FriendCompareForm, SteamIdForm, SyncSteamForm, ManualRateForm, EmptyForm
from datetime import datetime
from .steam_api import get_owned_games, resolve_to_steamid64
from .models import Rating, Game
from .steam_store_api import fetch_app_details
from bson import ObjectId
from .train import train_model
from .recommender import build_tag_vocab, user_to_vector


profile = Blueprint("profile", __name__, url_prefix="/profile")

def extract_appid(appid_input: str):
    """
    Accepts:
      - '620'
      - Steam store URLs like https://store.steampowered.com/app/620/Portal_2/
    Returns:
      int appid or None
    """
    appid_input = appid_input.strip()

    # Case 1: pure number
    if appid_input.isdigit():
        return int(appid_input)

    # Case 2: Steam store URL
    match = re.search(r"/app/(\d+)", appid_input)
    if match:
        return int(match.group(1))

    return None

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
        train_model()
        return redirect(url_for("profile.preferences"))

    return render_template("preferences.html", form=form)

@profile.route("/friend-compare", methods=["GET", "POST"])
@login_required
def friend_compare():
    form = FriendCompareForm(prefix="friend")

    result = None

    if form.validate_on_submit() and form.submit.data:
        friend_input = form.friend_steam.data.strip()

        try:
            friend_steamid64 = resolve_to_steamid64(friend_input)
            friend_games = get_owned_games(friend_steamid64)  # returns list of dicts with appid, playtime_forever, maybe name
        except Exception:
            return redirect(url_for("profile.friend_compare"))

        # Compute overlap (based on appids)
        my_owned = {g.get("appid") for g in (current_user.owned_games or []) if g.get("appid") is not None}
        friend_owned = {g.get("appid") for g in friend_games if g.get("appid") is not None}

        overlap = 0.0
        if my_owned or friend_owned:
            overlap = (len(my_owned & friend_owned) / len(my_owned | friend_owned)) * 100

        # Compute cosine similarity using vectors
        vocab = build_tag_vocab()
        me_vec = user_to_vector(current_user, vocab)

        # Build a "fake user-like object" for friend vector using their owned games only
        class FriendObj:
            id = None
            favorite_tags = []
            hated_tags = []
            owned_games = [{"appid": g.get("appid"), "playtime_forever": g.get("playtime_forever", 0)} for g in friend_games]

        friend_vec = user_to_vector(FriendObj(), vocab)

        # cosine similarity (manual, no sklearn needed here)
        def cos_sim(a, b):
            import math
            dot = sum(x*y for x, y in zip(a, b))
            na = math.sqrt(sum(x*x for x in a))
            nb = math.sqrt(sum(x*x for x in b))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        similarity = cos_sim(me_vec, friend_vec)

        result = {
            "friend_steamid64": friend_steamid64,
            "overlap_percent": round(overlap, 2),
            "similarity": round(similarity, 3),
            "my_count": len(my_owned),
            "friend_count": len(friend_owned),
            "shared_count": len(my_owned & friend_owned),
        }

    return render_template("friend_compare.html", form=form, result=result)

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

        # Enrich Games collection for owned appids (cap to avoid hammering API)
        owned_appids = [g["appid"] for g in current_user.owned_games[:200]]  # start with 50
        existing = set(Game.objects(appid__in=owned_appids).scalar("appid"))

        for appid in owned_appids:
            if appid not in existing:
                details = fetch_app_details(appid)
                if details:
                    Game(appid=details["appid"], name=details["name"], tags=details["tags"], global_rating=0.0).save()

        current_user.save()
        train_model()

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

@profile.route("/rate", methods=["GET", "POST"])
@login_required
def rate_game():
    form = ManualRateForm()

    if form.validate_on_submit():
        appid_int = extract_appid(form.appid.data)
        if not appid_int:
            return redirect(url_for("profile.rate_game"))

        game = Game.objects(appid=appid_int).first()
        if not game:
            details = fetch_app_details(appid_int)
            if not details:
                # invalid appid (or store API says success=false)
                return redirect(url_for("profile.rate_game"))

            Game(
                appid=details["appid"],
                name=details["name"],
                tags=details.get("tags", []),
                global_rating=0.0
            ).save()

        # Save rating (works whether user owns it or not)
        Rating.objects(user_id=current_user.id, appid=appid_int).modify(
            upsert=True,
            set__rating=form.rating.data,
            new=True
        )

        train_model()

        return redirect(url_for("profile.rate_game"))

    # Show user's recent ratings
    my_ratings = list(Rating.objects(user_id=current_user.id).order_by("-id")[:10])
    # Attach names if we have them
    ids = [r.appid for r in my_ratings]
    games = {g.appid: g.name for g in Game.objects(appid__in=ids).only("appid", "name")}
    ratings_view = [{"appid": r.appid, "name": games.get(r.appid), "rating": r.rating} for r in my_ratings]

    return render_template("rate.html", form=form, ratings=ratings_view, delete_form=EmptyForm())

@profile.route("/rate/delete/<int:appid>", methods=["POST"])
@login_required
def delete_rating(appid):
    Rating.objects(user_id=current_user.id, appid=appid).delete()
    train_model()
    return redirect(url_for("profile.rate_game"))

