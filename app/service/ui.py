import csv
import logging
from io import StringIO
from typing import Iterator
from uuid import UUID

from flask import Response as FlaskResponse
from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Service, Team
from app.service import ui_bp as ui
from app.service.forms import (
    ArchiveServiceForm,
    RestoreServiceForm,
    ServiceForm,
    ServiceSortFilterForm,
)
from app.service.service import (
    archive_service,
    create_service,
    download_services,
    get_service,
    get_services,
    restore_service,
    update_service,
)
from app.team.service import get_active_teams

logger = logging.getLogger(__name__)


@ui.route("/", methods=["GET"])
def list_services() -> ResponseReturnValue:
    form: ServiceSortFilterForm = ServiceSortFilterForm(request.args)

    page: int = request.args.get("page", 1, type=int)

    try:
        services: Pagination = get_services(
            sort=form.sort.data,
            status=form.status.data,
            page=page,
            per_page=form.per_page.data,
        )
    except SQLAlchemyError:
        logger.exception(
            f"Database error listing services (sort={form.sort.data},status={form.status.data},page={page},per_page={form.per_page.data})"
        )
        abort(503)

    return render_template(
        "list-services.html",
        title="Services",
        services=services,
        form=form,
    )


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form = ServiceForm()

    # Add options
    try:
        teams: list[Team] = get_active_teams()
    except SQLAlchemyError:
        logger.exception("Database error retrieving teams for create service form")
        abort(503)
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    if form.validate_on_submit():
        try:
            service = create_service(
                name=form.name.data,
                team_id=UUID(form.team.data) if form.team.data else None,
            )
            flash(
                f'<a href="{url_for("service_ui.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been created',
                "success",
            )
            logger.info("Created service id=%s name=%s", service.id, service.name)
            return redirect(url_for("service_ui.list_services"))
        except IntegrityError:
            form.name.errors.append("A service with this name already exists.")
            logger.warning("IntegrityError creating service name=%s", form.name.data, exc_info=True)
            return render_template("create-service.html", form=form)
        except SQLAlchemyError:
            logger.exception("Database error creating service name=%s", form.name.data)
            abort(503)
    return render_template("create-service.html", title="Add a new service", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    try:
        service: Service = get_service(id)
    except SQLAlchemyError:
        logger.exception("Database error viewing service %s", id)
        abort(503)
    return render_template("view-service.html", service=service)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    try:
        service: Service = get_service(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching service %s for edit", id)
        abort(503)
    form: ServiceForm = ServiceForm(service=service)

    # Add options
    try:
        teams: list[Team] = get_active_teams()
    except SQLAlchemyError:
        logger.exception("Database error retrieving teams for edit service form")
        abort(503)
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    if request.method == "GET":
        form.name.data = service.name
        form.team.data = str(service.team_id)
    elif form.validate_on_submit():
        try:
            update_service(
                id=id,
                name=form.name.data,
                team_id=UUID(form.team.data) if form.team.data else None,
            )
            flash(
                f'<a href="{url_for("service_ui.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been updated',
                "success",
            )
            logger.info("Updated service id=%s", id)
            return redirect(url_for("service_ui.list_services"))
        except IntegrityError:
            form.name.errors.append("A service with this name already exists.")
        except SQLAlchemyError:
            logger.exception("Database error updating service %s", id)
            abort(503)

    return render_template("edit-service.html", title="Edit service", service=service, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    try:
        service: Service = get_service(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching service %s for archive", id)
        abort(503)
    form: ArchiveServiceForm = ArchiveServiceForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            archive_service(id)
            logger.info("Archived service %s", id)
            flash(
                f'<a href="{url_for("service_ui.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been archived',
                "success",
            )
            return redirect(url_for("service_ui.list_services"))
        except SQLAlchemyError:
            logger.exception("Database error archiving service %s", id)
            abort(503)

    return render_template("archive-service.html", title="Archive service", service=service, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    try:
        service: Service = get_service(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching service %s for restore", id)
        abort(503)
    form: RestoreServiceForm = RestoreServiceForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            restore_service(id)
            logger.info("Restored service %s", id)
            flash(
                f'<a href="{url_for("service_ui.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been restored',
                "success",
            )
            return redirect(url_for("service_ui.list_services"))
        except SQLAlchemyError:
            logger.exception("Database error restoring service %s", id)
            abort(503)

    return render_template("restore-service.html", title="Restore service", service=service, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    try:
        services: list[Service] = download_services()
    except SQLAlchemyError:
        logger.exception("Database error downloading services")
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
                "TEAM_ID",
                "TEAM_NAME",
                "UPDATED_AT",
                "ARCHIVED_AT",
            )
        )
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        for service in services:
            writer.writerow(
                (
                    service.id,
                    service.name,
                    service.team.id if service.team else "",
                    service.team.name if service.team else "",
                    service.updated_at.isoformat(),
                    service.archived_at.isoformat() if service.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="services.csv")
    return response
