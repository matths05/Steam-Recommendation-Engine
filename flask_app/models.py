from flask_login import UserMixin
from . import db

class User(db.Document, UserMixin):
    email = db.StringField(required=True, unique=True)
    password_hash = db.StringField(required=True)

    favorite_tags = db.ListField(db.StringField(), default=list)
    hated_tags = db.ListField(db.StringField(), default=list)

    friend_steam_id = db.StringField()

    steam_id = db.StringField()
    owned_games = db.ListField(db.DictField(), default=list)   # each dict: {"appid": int, "playtime_forever": int}
    last_sync = db.DateTimeField()

    # This tells MongoEngine which collection name to use (optional but nice)
    meta = {"collection": "users"}

    pinned_games = db.ListField(db.IntField(), default=list)

    calculated_vector = db.ListField(db.FloatField(), default=list)

    def get_id(self):
        # Flask-Login needs a string ID
        return str(self.id)
    
class Game(db.Document):
    appid = db.IntField(required=True, unique=True)
    name = db.StringField(required=True)
    tags = db.ListField(db.StringField(), default=list)
    global_rating = db.FloatField(default=0.0)  # 0-10 or 0-100, your choice

    meta = {"collection": "games"}

class Rating(db.Document):
    user_id = db.ObjectIdField(required=True)
    appid = db.IntField(required=True)
    rating = db.IntField(required=True, min_value=1, max_value=10)

    meta = {
        "collection": "ratings",
        "indexes": [
            {"fields": ["user_id", "appid"], "unique": True}
        ]
    }


