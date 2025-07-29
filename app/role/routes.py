from flask import render_template

from app.role import bp


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-roles.html")
