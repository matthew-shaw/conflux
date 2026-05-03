import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Iterator
from uuid import UUID

from flask import Response as FlaskResponse
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role
from app.role import ui_bp as ui
from app.role.forms import (
    ArchiveRoleForm,
    RestoreRoleForm,
    RoleForm,
    RoleSortFilterForm,
)
from app.role.service import get_role, get_roles


@ui.route("/", methods=["GET"])
def list_roles() -> ResponseReturnValue:
    form: RoleSortFilterForm = RoleSortFilterForm()
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    roles = get_roles(
        sort=form.sort.data,
        status=form.status.data,
    )

    return render_template("list-roles.html", title="Roles", roles=roles, form=form)


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form: RoleForm = RoleForm()
    form.grade.choices = [(grade, grade) for grade in current_app.config["GRADES"]]
    if form.validate_on_submit():
        role: Role = Role(name=form.name.data, grade=form.grade.data)
        db.session.add(role)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been created',
                "success",
            )
            return redirect(url_for("role_ui.list_roles"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")
            return render_template("create-role.html", form=form)
    return render_template("create-role.html", title="Add a new role", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    role = get_role(id)
    return render_template("view-role.html", role=role)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
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
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("role_ui.list_roles"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A role with this name already exists.")

    return render_template("edit-role.html", title="Edit role", role=role, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    role: Role = db.get_or_404(Role, id)
    form: ArchiveRoleForm = ArchiveRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("role_ui.list_roles"))

    return render_template("archive-role.html", title="Archive role", role=role, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    role: Role = db.get_or_404(Role, id)
    form: RestoreRoleForm = RestoreRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        role.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("role_ui.list_roles"))

    return render_template("restore-role.html", title="Restore role", role=role, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    roles: list[Role] = list(db.session.execute(db.select(Role).order_by(Role.name)).scalars().all())

    def generate() -> Iterator[str]:
        data = StringIO()
        writer = csv.writer(data, quoting=csv.QUOTE_MINIMAL)

        # Add BOM (Byte Order Mark) for Excel compatibility
        yield "\ufeff"  # This signals that the file is UTF-8 encoded

        # write header
        writer.writerow(("ID", "NAME", "GRADE", "UPDATED_AT", "ARCHIVED_AT"))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        for role in roles:
            writer.writerow(
                (
                    role.id,
                    role.name,
                    role.grade,
                    role.updated_at.isoformat(),
                    role.archived_at.isoformat() if role.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="roles.csv")
    return response
