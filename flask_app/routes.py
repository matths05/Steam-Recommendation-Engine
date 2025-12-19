from flask import Blueprint, render_template
from . import db

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("home.html")

@main.route("/db-test")
def db_test():
    database = db.connection.get_database()  # uses the db name in your URI
    database.test_collection.insert_one({"message": "hello from atlas"})
    doc = database.test_collection.find_one(sort=[("_id", -1)])
    return doc["message"]
