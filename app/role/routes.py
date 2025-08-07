import csv
from datetime import datetime, timezone
from io import StringIO
from typing import List
from uuid import UUID

from flask import (
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
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
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    # Start the base SELECT statement
    query = db.Select(Role)

    # Apply sorting
    sort = form.sort.data or "name"
    if sort == "name":
        query = query.order_by(Role.name)
    elif sort == "grade":
        query = query.order_by(Role.grade)
    elif sort == "updated":
        query = query.order_by(Role.updated_at.desc())

    # Apply filter based on status
    status = form.status.data or "active"
    if status == "active":
        query = query.where(Role.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Role.archived_at.is_not(None))
    # No filter if status == "all"

    roles: List[Role] = db.session.execute(query).scalars().all()

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


@bp.route("/download", methods=["GET"])
def download():
    roles: List[Role] = db.session.execute(db.Select(Role).order_by(Role.name)).scalars().all()

    def generate():
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

    response = Response(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="roles.csv")
    return response
