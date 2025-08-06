from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role
from app.role import bp
from app.role.forms import ArchiveRoleForm, RestoreRoleForm, RoleForm
from app.utils.govuk_datetime_utils import format_govuk_datetime


@bp.route("/", methods=["GET"])
def list() -> str:
    roles: List[Role] = Role.query.order_by(Role.name).all()
    # Format the roles as a list of lists of dicts, as required by the GOV.UK table macro.
    # Each inner list represents a table row, and each dict represents a cell with a "text" key.
    rows: List[List[Dict[str, Any]]] = [
        [
            {"html": f'<a href="{url_for("role.view", id=role.id)}" class="govuk-link">{role.name}</a>'},
            {"text": "Archived" if role.archived_at else "Active"},
            {"text": format_govuk_datetime(role.updated_at, include_day=False)},
        ]
        for role in roles
    ]
    return render_template("list-roles.html", title="Roles", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    form: RoleForm = RoleForm()
    if form.validate_on_submit():
        role: Role = Role(name=form.name.data)
        db.session.add(role)
        try:
            db.session.commit()
            flash(f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been created', 'success')
            return redirect(url_for("role.list"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")
            return render_template("create-role.html", form=form)
    return render_template("create-role.html", title="Create a new role", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> str:
    role = Role.query.get_or_404(id)
    role.updated_at = format_govuk_datetime(role.updated_at, include_time=True, include_day=False)
    return render_template("view-role.html", role=role)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> str:
    role: Role = Role.query.get_or_404(id)
    form: RoleForm = RoleForm()

    if request.method == "GET":
        form.name.data = role.name
    elif form.validate_on_submit():
        role.name = form.name.data
        try:
            db.session.commit()
            flash(f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been updated', 'success')
            return redirect(url_for("role.view", id=role.id))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")

    return render_template("edit-role.html", title="Edit role", form=form, role=role)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> str:
    role: Role = Role.query.get_or_404(id)
    form: ArchiveRoleForm = ArchiveRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been archived', 'success')
        return redirect(url_for("role.list"))

    return render_template("archive-role.html", title="Archive role", role=role, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> str:
    role: Role = Role.query.get_or_404(id)
    form: RestoreRoleForm = RestoreRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = None
        db.session.commit()
        flash(f'<a href="{url_for("role.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been restored', 'success')
        return redirect(url_for("role.list"))

    return render_template("restore-role.html", title="Restore role", role=role, form=form)
