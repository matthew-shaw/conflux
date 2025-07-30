from flask import flash, redirect, render_template, url_for

from app.role import bp
from app.role.forms import RoleForm


@bp.route("/", methods=["GET", "POST"])
def list():
    return render_template("list-roles.html")


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = RoleForm()
    if form.validate_on_submit():
        flash(f"The {form.title.data} role has been created", "success")
        return redirect(url_for("role.list"))
    return render_template("create-role.html", form=form)
