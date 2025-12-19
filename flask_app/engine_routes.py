from flask import Blueprint
from flask_login import login_required, current_user

engine = Blueprint("engine", __name__, url_prefix="/engine")

@engine.route("/recommendations")
@login_required
def recommendations():
    # placeholder: just show how many games we have to work with
    owned = current_user.owned_games or []
    return {
        "owned_games_count": len(owned),
        "message": "Engine route works. Next: real recommendations."
    }
