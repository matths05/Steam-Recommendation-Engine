from flask import Blueprint, render_template, abort
from flask_login import login_required
from .models import Game

explore = Blueprint("explore", __name__, url_prefix="/explore")

@explore.route("/game/<int:appid>")
@login_required
def game_detail(appid):
    game = Game.objects(appid=appid).first()
    if not game:
        abort(404)
    return render_template("game_detail.html", game=game)

@explore.route("/genre/<tag>")
@login_required
def genre_page(tag):
    # Case-sensitive tags can be annoying; keep it simple for now.
    games = list(Game.objects(tags=tag).order_by("-global_rating")[:50])
    return render_template("genre.html", tag=tag, games=games)
