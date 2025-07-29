from flask import render_template

from app.component import bp


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-components.html")
