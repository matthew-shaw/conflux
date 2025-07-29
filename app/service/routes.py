from flask import render_template

from app.service import bp


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-services.html")
