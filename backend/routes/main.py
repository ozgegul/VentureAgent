from flask import Blueprint, render_template, session

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    session.pop("guided_state", None)
    return render_template("index.html")
