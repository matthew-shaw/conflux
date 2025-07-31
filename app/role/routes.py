from uuid import UUID

from flask import flash, redirect, render_template, url_for

from app import db
from app.models import Role
from app.role import bp
from app.role.forms import RoleForm


@bp.route("/", methods=["GET"])
def list() -> str:
    return render_template("list-roles.html")


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    form: RoleForm = RoleForm()
    if form.validate_on_submit():
        flash(f"{form.title.data} has been created", "success")
        return redirect(url_for("role.list"))
    return render_template("create-role.html", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> str:
    return render_template("view-role.html")


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> str:
    return render_template("edit-role.html")


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> str:
    return render_template("archive-role.html")
