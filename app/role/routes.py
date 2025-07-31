from flask import flash, redirect, render_template, url_for

from app import db
from app.models import Role
from app.role import bp
from app.role.forms import RoleForm


@bp.route("/", methods=["GET"])
def list():
    return render_template("list-roles.html")


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = RoleForm()
    if form.validate_on_submit():
        flash(f"{form.title.data} has been created", "success")
        return redirect(url_for("role.list"))
    return render_template("create-role.html", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id):
    pass


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id):
    pass


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id):
    pass
