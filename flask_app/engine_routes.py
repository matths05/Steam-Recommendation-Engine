from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Game, User
from flask_wtf import FlaskForm
from sklearn.neighbors import NearestNeighbors
from .recommender import build_tag_vocab, build_training_data, user_to_vector
from .steam_store_api import fetch_app_details

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

@engine.route("/train_model")
@login_required
def train_model():
    vocab = build_tag_vocab()
    user_ids, X = build_training_data(vocab)

    # Save each user's calculated_vector in MongoDB (so you can show you computed it)
    # Recompute per user so it matches same vocab
    for uid in user_ids:
        u = User.objects(id=uid).first()
        if u:
            u.calculated_vector = user_to_vector(u, vocab)
            u.save()

    return {
        "tags_in_vocab": len(vocab),
        "users_trained": len(user_ids),
        "note": "Vectors stored in users.calculated_vector. KNN fitting happens in recommendations route."
    }

@engine.route("/knn_recommendations")
@login_required
def knn_recommendations():
    vocab = build_tag_vocab()
    user_ids, X = build_training_data(vocab)

    # Need at least 2 users for "neighbors"
    if len(user_ids) < 2:
        return {
            "error": "Need at least 2 users with preference data to run KNN. Create another account and set preferences.",
            "users_trained": len(user_ids)
        }

    # Fit KNN (cosine distance)
    knn = NearestNeighbors(n_neighbors=min(5, len(user_ids)), metric="cosine")
    knn.fit(X)

    me_vec = user_to_vector(current_user, vocab)
    distances, indices = knn.kneighbors([me_vec], n_neighbors=min(5, len(user_ids)))

    # Map neighbor indices -> User docs (skip yourself)
    neighbor_ids = []
    for i in indices[0]:
        uid = user_ids[i]
        if uid != str(current_user.id):
            neighbor_ids.append(uid)

    neighbors = list(User.objects(id__in=neighbor_ids))

    # Recommend games neighbors pinned (simple + demo-friendly)
    my_owned_ids = {g.get("appid") for g in (current_user.owned_games or []) if g.get("appid") is not None}
    my_pins = set(current_user.pinned_games or [])

    candidate_scores = {}  # appid -> score
    for n in neighbors:
        for appid in (n.pinned_games or []):
            if appid in my_owned_ids or appid in my_pins:
                continue
            candidate_scores[appid] = candidate_scores.get(appid, 0) + 1

    # Look up game details
    rec_ids = sorted(candidate_scores.keys(), key=lambda a: candidate_scores[a], reverse=True)[:10]
    games = list(Game.objects(appid__in=rec_ids))
    by_id = {g.appid: g for g in games}

    recs = []
    for appid in rec_ids:
        g = by_id.get(appid)
        if g:
            recs.append({
                "appid": appid,
                "name": g.name,
                "tags": g.tags,
                "global_rating": g.global_rating,
                "neighbor_votes": candidate_scores[appid],
            })

    return {
        "neighbors_used": [str(n.email) for n in neighbors],
        "recommendations": recs
    }

@engine.route("/knn", methods=["GET"])
@login_required
def knn_page():
    vocab = build_tag_vocab()
    user_ids, X = build_training_data(vocab)

    if len(user_ids) < 2:
        return render_template("knn.html", error="Need at least 2 users with preferences.", neighbors=[], recs=[], form=EmptyForm())

    knn = NearestNeighbors(n_neighbors=min(5, len(user_ids)), metric="cosine")
    knn.fit(X)

    me_vec = user_to_vector(current_user, vocab)
    distances, indices = knn.kneighbors([me_vec], n_neighbors=min(5, len(user_ids)))

    neighbors_info = []
    neighbor_ids = []
    for dist, idx in zip(distances[0], indices[0]):
        uid = user_ids[idx]
        if uid == str(current_user.id):
            continue
        neighbor_ids.append(uid)
        neighbors_info.append({"user_id": uid, "distance": float(dist), "similarity": round(1 - float(dist), 3)})

    neighbors = list(User.objects(id__in=neighbor_ids).only("email", "owned_games", "pinned_games"))
    by_id = {str(u.id): u for u in neighbors}

    # Recommend from neighbors' owned libraries (not just pins)
    my_owned_ids = {g.get("appid") for g in (current_user.owned_games or []) if g.get("appid") is not None}
    my_pins = set(current_user.pinned_games or [])

    scores = {}  # appid -> float score

    for info in neighbors_info:
        u = by_id.get(info["user_id"])
        if not u:
            continue

        sim = info["similarity"]  # 0..1
        for og in (u.owned_games or []):
            appid = og.get("appid")
            if appid is None:
                continue
            if appid in my_owned_ids or appid in my_pins:
                continue

            hours = (og.get("playtime_forever", 0) or 0) / 60.0

            # Score contribution: similarity-weighted hours (cap hours so one game doesn't dominate)
            contrib = sim * min(hours, 100)

            scores[appid] = scores.get(appid, 0.0) + contrib

    rec_ids = sorted(scores.keys(), key=lambda a: scores[a], reverse=True)[:10]
    missing = [appid for appid in rec_ids if not Game.objects(appid=appid).first()]
    for appid in missing:
        details = fetch_app_details(appid)
        if details:
            Game(appid=details["appid"], name=details["name"], tags=details["tags"], global_rating=0.0).save()
    games = list(Game.objects(appid__in=rec_ids))
    by_game = {g.appid: g for g in games}

    recs = []
    for appid in rec_ids:
        g = by_game.get(appid)
        recs.append({
            "appid": appid,
            "name": g.name if g else f"AppID {appid}",
            "tags": g.tags if g else [],
            "score": round(scores[appid], 2),
        })

    # Add neighbor emails
    for info in neighbors_info:
        u = by_id.get(info["user_id"])
        info["email"] = u.email if u else "(unknown)"

    return render_template(
        "knn.html",
        error=None,
        neighbors=neighbors_info,
        recs=recs,
        pinned=set(current_user.pinned_games or []),
        form=EmptyForm()
    )

