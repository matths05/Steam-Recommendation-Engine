import os
from flask import Flask
from flask_mongoengine import MongoEngine
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


db = MongoEngine()

login_manager = LoginManager()
login_manager.login_view = "auth.login"

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-later")

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")
    
    app.config["MONGODB_SETTINGS"] = {"host": mongo_uri}

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.objects(id=user_id).first()


    from .routes import main
    app.register_blueprint(main)

    from .auth_routes import auth
    app.register_blueprint(auth)

    from .profile_routes import profile
    app.register_blueprint(profile)

    return app
