from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Game
from flask_wtf import FlaskForm

engine = Blueprint("engine", __name__, url_prefix="/engine")

class EmptyForm(FlaskForm):
    pass

@engine.route("/recommendations")
@login_required
def recommendations():
    owned = current_user.owned_games or []
    owned_ids = {g.get("appid") for g in owned if g.get("appid") is not None}

    fav = set(current_user.favorite_tags or [])
    hate = set(current_user.hated_tags or [])

    # Pull candidates from DB (exclude owned)
    candidates = Game.objects(appid__nin=list(owned_ids))[:200]  # cap to keep it fast

    scored = []
    for game in candidates:
        tags = set(game.tags or [])
        # simple scoring
        score = 0
        score += 3 * len(tags & fav)      # reward favorite overlap
        score -= 5 * len(tags & hate)     # penalize hated overlap
        score += (game.global_rating or 0) / 2  # rating influence (tweak anytime)

        scored.append({
            "appid": game.appid,
            "name": game.name,
            "tags": game.tags,
            "global_rating": game.global_rating,
            "score": round(score, 2),
            "fav_overlap": list(tags & fav),
            "hate_overlap": list(tags & hate),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:10]

    return {"recommendations": top, "count_considered": len(scored)}

@engine.route("/seed-games")
@login_required
def seed_games():
    sample = [
        {"appid": 620, "name": "Portal 2", "tags": ["Puzzle", "Adventure"], "global_rating": 9.5},
        {"appid": 570, "name": "Dota 2", "tags": ["Strategy", "Action"], "global_rating": 8.8},
        {"appid": 730, "name": "CS2", "tags": ["Action"], "global_rating": 8.2},
        {"appid": 440, "name": "Team Fortress 2", "tags": ["Action"], "global_rating": 8.6},
        {"appid": 105600, "name": "Terraria", "tags": ["Adventure", "Simulation"], "global_rating": 9.0},
        {"appid": 413150, "name": "Stardew Valley", "tags": ["Simulation", "Puzzle"], "global_rating": 9.2},
        {"appid": 381210, "name": "Dead by Daylight", "tags": ["Horror", "Action"], "global_rating": 8.0},
    ]

    upserted = 0
    for g in sample:
        res = Game.objects(appid=g["appid"]).modify(upsert=True, new=True, **g)
        upserted += 1

    return {"seeded": upserted}

@engine.route("/recommendations-page", methods=["GET"])
@login_required
def recommendations_page():
    owned = current_user.owned_games or []
    owned_ids = {g.get("appid") for g in owned if g.get("appid") is not None}

    fav = set(current_user.favorite_tags or [])
    hate = set(current_user.hated_tags or [])

    candidates = Game.objects(appid__nin=list(owned_ids))[:200]

    scored = []
    for game in candidates:
        tags = set(game.tags or [])
        score = 0
        score += 3 * len(tags & fav)
        score -= 5 * len(tags & hate)
        score += (game.global_rating or 0) / 2

        scored.append({
            "appid": game.appid,
            "name": game.name,
            "tags": game.tags,
            "global_rating": game.global_rating,
            "score": round(score, 2),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:10]

    form = EmptyForm()
    pinned = set(current_user.pinned_games or [])

    return render_template("recommendations.html", recs=top, form=form, pinned=pinned)

@engine.route("/pin/<int:appid>", methods=["POST"])
@login_required
def pin(appid):
    form = EmptyForm()
    if form.validate_on_submit():
        if appid not in (current_user.pinned_games or []):
            current_user.pinned_games.append(appid)
            current_user.save()
    return redirect(url_for("engine.recommendations_page"))

@engine.route("/unpin/<int:appid>", methods=["POST"])
@login_required
def unpin(appid):
    form = EmptyForm()
    if form.validate_on_submit():
        current_user.pinned_games = [x for x in (current_user.pinned_games or []) if x != appid]
        current_user.save()
    return redirect(url_for("engine.wishlist"))

@engine.route("/wishlist", methods=["GET"])
@login_required
def wishlist():
    pinned_ids = current_user.pinned_games or []
    games = list(Game.objects(appid__in=pinned_ids))

    # preserve the user's pin order
    by_id = {g.appid: g for g in games}
    ordered = [by_id[a] for a in pinned_ids if a in by_id]

    form = EmptyForm()
    return render_template("wishlist.html", games=ordered, form=form)

