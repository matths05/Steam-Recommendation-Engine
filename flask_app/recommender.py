from __future__ import annotations
from collections import defaultdict
from typing import List, Tuple
from .models import Game, User, Rating


def build_tag_vocab() -> List[str]:
    """
    Build a stable tag vocabulary from your Games collection.
    Keep it deterministic so user vectors line up across users.
    """
    tags = set()
    for g in Game.objects.only("tags"):
        for t in (g.tags or []):
            tags.add(t)
    return sorted(tags)


def user_to_vector(user: User, vocab: List[str]) -> List[float]:
    """
    Vector definition:
      - Start with zeros for each tag in vocab.
      - Add +3 for each favorite tag
      - Add -5 for each hated tag
      - Add playtime contribution from owned games *if* we have tags for those appids in Games collection
    """
    idx = {t: i for i, t in enumerate(vocab)}
    v = [0.0] * len(vocab)

    fav = set(user.favorite_tags or [])
    hate = set(user.hated_tags or [])

    for t in fav:
        if t in idx:
            v[idx[t]] += 3.0

    for t in hate:
        if t in idx:
            v[idx[t]] -= 5.0

    # optional: use owned playtime to strengthen signals (only works where appid exists in Games collection)
    owned = user.owned_games or []
    owned_by_appid = {g.get("appid"): g for g in owned if g.get("appid") is not None}
    owned_appids = list(owned_by_appid.keys())

    # Pull manual ratings for this user (appid -> rating 1..10)
    ratings = {
        r.appid: r.rating
        for r in Rating.objects(user_id=user.id, appid__in=owned_appids).only("appid", "rating")
    }

    if owned_appids:
        games = Game.objects(appid__in=owned_appids).only("appid", "tags")
        for game in games:
            tags = game.tags or []

            if game.appid in ratings:
                # Rating overrides hours:
                # Convert rating 1..10 into a centered weight (-1.0 .. +1.0)
                # 1 -> -1.0, 5/6 -> around 0, 10 -> +1.0
                w = (ratings[game.appid] - 5.5) / 4.5
                # Make ratings a strong signal
                for t in tags:
                    if t in idx:
                        v[idx[t]] += 3.0 * w
            else:
                # Otherwise use hours as a weak signal
                minutes = owned_by_appid.get(game.appid, {}).get("playtime_forever", 0) or 0
                hours = minutes / 60.0
                for t in tags:
                    if t in idx:
                        v[idx[t]] += 0.1 * hours

    return v


def build_training_data(vocab: List[str]) -> Tuple[List[str], List[List[float]]]:
    """
    Returns (user_ids, vectors) for users that have at least some signal.
    """
    user_ids = []
    vectors = []
    for u in User.objects.only("favorite_tags", "hated_tags", "owned_games"):
        vec = user_to_vector(u, vocab)
        # skip all-zero vectors
        if any(abs(x) > 1e-9 for x in vec):
            user_ids.append(str(u.id))
            vectors.append(vec)
    return user_ids, vectors
