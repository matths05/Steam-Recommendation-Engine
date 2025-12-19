from flask_login import UserMixin
from . import db

class User(db.Document, UserMixin):
    email = db.StringField(required=True, unique=True)
    password_hash = db.StringField(required=True)

    # This tells MongoEngine which collection name to use (optional but nice)
    meta = {"collection": "users"}

    def get_id(self):
        # Flask-Login needs a string ID
        return str(self.id)
