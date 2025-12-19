import os
from flask import Flask
from flask_mongoengine import MongoEngine

db = MongoEngine()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-later")

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")
    
    app.config["MONGODB_SETTINGS"] = {"host": mongo_uri}

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app
