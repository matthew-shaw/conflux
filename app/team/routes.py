from flask import render_template

from app.team import bp


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-teams.html")
