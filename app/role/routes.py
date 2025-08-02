from typing import Any, Dict, List
from uuid import UUID

from flask import flash, redirect, render_template, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role
from app.role import bp
from app.role.forms import RoleForm
from app.utils.govuk_datetime_utils import format_govuk_datetime

@bp.route("/", methods=["GET"])
def list() -> str:
    roles: List[Role] = Role.query.order_by(Role.title).all()
    # Format the roles as a list of lists of dicts, as required by the GOV.UK table macro.
    # Each inner list represents a table row, and each dict represents a cell with a "text" key.
    rows: List[List[Dict[str, Any]]] = [
        [
            {"html": f'<a href="{url_for("role.view", id=role.id)}" class="govuk-link">{role.title}</a>'},
            {"text": format_govuk_datetime(role.updated_at, include_day=False)},
        ]
        for role in roles
    ]
    return render_template("list-roles.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    form: RoleForm = RoleForm()
    if form.validate_on_submit():
        role: Role = Role(title=form.title.data)
        db.session.add(role)
        try:
            db.session.commit()
            flash(f"{form.title.data} has been created", "success")
            return redirect(url_for("role.list"))
        except IntegrityError:
            db.session.rollback()
            form.title.errors.append("A role with this title already exists.")
            return render_template("create-role.html", form=form)
    return render_template("create-role.html", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> str:
    role = Role.query.get_or_404(id)
    role.updated_at = format_govuk_datetime(role.updated_at, include_time=True, include_day=False)
    return render_template("view-role.html", role=role)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> str:
    return render_template("edit-role.html")


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> str:
    return render_template("archive-role.html")
