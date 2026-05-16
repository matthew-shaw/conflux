import csv
import logging
from io import StringIO
from typing import Iterator
from uuid import UUID

from flask import Response as FlaskResponse
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Role
from app.role import ui_bp as ui
from app.role.forms import (
    ArchiveRoleForm,
    RestoreRoleForm,
    RoleForm,
    RoleSortFilterForm,
)
from app.role.service import (
    archive_role,
    create_role,
    download_roles,
    get_role,
    get_roles,
    restore_role,
    update_role,
)

logger = logging.getLogger(__name__)


@ui.route("/", methods=["GET"])
def list_roles() -> ResponseReturnValue:
    form: RoleSortFilterForm = RoleSortFilterForm(request.args)

    page: int = request.args.get("page", 1, type=int)

    try:
        roles: Pagination = get_roles(
            sort=form.sort.data,
            status=form.status.data,
            page=page,
            per_page=form.per_page.data,
        )
    except SQLAlchemyError:
        logger.exception(
            f"Database error listing roles (sort={form.sort.data},status={form.status.data},page={page},per_page={form.per_page.data})"
        )
        abort(503)

    return render_template(
        "list-roles.html",
        title="Roles",
        roles=roles,
        form=form,
    )


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form: RoleForm = RoleForm()

    # Add options
    form.grade.choices = [(grade, grade) for grade in current_app.config["GRADES"]]

    if form.validate_on_submit():
        try:
            role = create_role(
                name=form.name.data,
                grade=form.grade.data,
            )
            flash(
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been created',
                "success",
            )
            logger.info(f"Created role id={role.id} name={role.name}")
            return redirect(url_for("role_ui.list_roles"))
        except IntegrityError:
            form.name.errors.append("A role with this name already exists.")
            logger.warning(f"IntegrityError creating role name={form.name.data}", exc_info=True)
            return render_template("create-role.html", form=form)
        except SQLAlchemyError:
            logger.exception(f"Database error creating role name={form.name.data}")
            abort(503)
    return render_template("create-role.html", title="Add a new role", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    try:
        role: Role = get_role(id)
    except SQLAlchemyError:
        logger.exception(f"Database error viewing role {id}")
        abort(503)
    return render_template("view-role.html", role=role)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    try:
        role: Role = get_role(id)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching role {id} for edit")
        abort(503)
    form: RoleForm = RoleForm(role=role)

    # Add options
    form.grade.choices = [(grade, grade) for grade in current_app.config["GRADES"]]

    if request.method == "GET":
        form.name.data = role.name
        form.grade.data = role.grade
    elif form.validate_on_submit():
        try:
            update_role(
                id=id,
                name=form.name.data,
                grade=form.grade.data,
            )
            flash(
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been updated',
                "success",
            )
            logger.info(f"Updated role id={role.id} name={form.name.data}")
            return redirect(url_for("role_ui.list_roles"))
        except IntegrityError:
            form.name.errors.append("A role with this name already exists.")
            logger.warning(
                f"IntegrityError updating role id={id} name={form.name.data}",
                exc_info=True,
            )
        except SQLAlchemyError:
            logger.exception(f"Database error updating role {id}")
            abort(503)

    return render_template("edit-role.html", title="Edit role", role=role, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    try:
        role: Role = get_role(id)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching role for archive {id}")
        abort(503)
    form: ArchiveRoleForm = ArchiveRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            archive_role(id)
            logger.info(f"Archived role {id}")
            flash(
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been archived',
                "success",
            )
            return redirect(url_for("role_ui.list_roles"))
        except SQLAlchemyError:
            logger.exception(f"Database error archiving role {id}")
            abort(503)

    return render_template("archive-role.html", title="Archive role", role=role, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    try:
        role: Role = get_role(id)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching role for restore {id}")
        abort(503)
    form: RestoreRoleForm = RestoreRoleForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            restore_role(id)
            logger.info(f"Restored role {id}")
            flash(
                f'<a href="{url_for("role_ui.view", id=role.id)}" class="govuk-notification-banner__link">{role.name}</a> has been restored',
                "success",
            )
            return redirect(url_for("role_ui.list_roles"))
        except SQLAlchemyError:
            logger.exception(f"Database error restoring role {id}")
            abort(503)

    return render_template("restore-role.html", title="Restore role", role=role, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    try:
        roles: list[Role] = download_roles()
    except SQLAlchemyError:
        logger.exception("Database error downloading roles")
        abort(503)

    def generate() -> Iterator[str]:
        data = StringIO()
        writer = csv.writer(data, quoting=csv.QUOTE_MINIMAL)

        # Add BOM (Byte Order Mark) for Excel compatibility
        yield "\ufeff"  # This signals that the file is UTF-8 encoded

        # write header
        writer.writerow(
            (
                "ID",
                "NAME",
                "GRADE",
                "UPDATED_AT",
                "ARCHIVED_AT",
            )
        )
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
