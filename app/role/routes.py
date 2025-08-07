from datetime import datetime, timezone
from typing import List
from uuid import UUID

from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role
from app.role import bp
from app.role.forms import (
    ArchiveRoleForm,
    RestoreRoleForm,
    RoleForm,
    RoleSortFilterForm,
)


@bp.route("/", methods=["GET"])
def list() -> str:
    form: RoleSortFilterForm = RoleSortFilterForm()
    roles: List[Role] = db.session.execute(db.select(Role).filter_by(archived_at=None).order_by(Role.name)).scalars()
    return render_template("list-roles.html", title="Roles", roles=roles, form=form)


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    form: RoleForm = RoleForm()
    form.grade.choices = [(grade, grade) for grade in current_app.config["GRADES"]]
    if form.validate_on_submit():
        role: Role = Role(name=form.name.data, grade=form.grade.data)
        db.session.add(role)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been created',
                "success",
            )
            return redirect(url_for("role.list"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")
            return render_template("create-role.html", form=form)
    return render_template("create-role.html", title="Create a new role", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> str:
    role = db.get_or_404(Role, id)
    return render_template("view-role.html", role=role)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> str:
    role: Role = db.get_or_404(Role, id)
    form: RoleForm = RoleForm()
    form.grade.choices = [(grade, grade) for grade in current_app.config["GRADES"]]

    if request.method == "GET":
        form.name.data = role.name
        form.grade.data = role.grade
    elif form.validate_on_submit():
        role.name = form.name.data
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("role.view", id=role.id))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")

    return render_template("edit-role.html", title="Edit role", role=role, form=form)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> str:
    role: Role = db.get_or_404(Role, id)
    form: ArchiveRoleForm = ArchiveRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("role.list"))

    return render_template("archive-role.html", title="Archive role", role=role, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> str:
    role: Role = db.get_or_404(Role, id)
    form: RestoreRoleForm = RestoreRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("role.list"))

    return render_template("restore-role.html", title="Restore role", role=role, form=form)
