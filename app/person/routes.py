from flask import render_template

from app.person import bp


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-people.html")
