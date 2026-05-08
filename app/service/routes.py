import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Iterator
from uuid import UUID

from flask import Response as FlaskResponse
from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app import db
from app.models import Service, Team
from app.person import service
from app.service import bp
from app.service.forms import (
    ArchiveServiceForm,
    RestoreServiceForm,
    ServiceForm,
    ServiceSortFilterForm,
)
from app.team.service import get_teams


@bp.route("/", methods=["GET"])
def list_services() -> ResponseReturnValue:
    form: ServiceSortFilterForm = ServiceSortFilterForm()
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    # Start the base SELECT statement
    query = db.select(Service)

    # Apply sorting
    sort = form.sort.data or "name"
    if sort == "name":
        query = query.order_by(Service.name)
    elif sort == "updated":
        query = query.order_by(Service.updated_at.desc())

    # Apply filter based on status
    status = form.status.data or "active"
    if status == "active":
        query = query.where(Service.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Service.archived_at.is_not(None))
    # No filter if status == "all"

    services: list[Service] = list(db.session.execute(query).scalars().all())

    return render_template("list-services.html", title="Services", services=services, form=form)


@bp.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form: ServiceForm = ServiceForm()

    # Add options
    teams: list[Team] = get_teams()
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    if form.validate_on_submit():
        service: Service = Service(
            name=form.name.data,
            team_id=UUID(form.team.data) if form.team.data else None,
        )
        db.session.add(service)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("service.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been created',
                "success",
            )
            return redirect(url_for("service.list_services"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A service with this name already exists.")
            return render_template("create-service.html", form=form)
    return render_template("create-service.html", title="Add a new service", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    service = db.get_or_404(Service, id)
    return render_template("view-service.html", service=service)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    service: Service = db.get_or_404(Service, id)
    form: ServiceForm = ServiceForm()
    form.service = service

    # Add options
    teams: list[Team] = get_teams()
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    if request.method == "GET":
        form.name.data = service.name
        form.team.data = str(service.team_id)
    elif form.validate_on_submit():
        service.name = form.name.data
        service.team_id = UUID(form.team.data) if form.team.data else None
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("service.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("service.list_services"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A service with this name already exists.")

    return render_template("edit-service.html", title="Edit service", service=service, form=form)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    service: Service = db.get_or_404(Service, id)
    form: ArchiveServiceForm = ArchiveServiceForm()

    if form.validate_on_submit() and form.confirm.data is True:
        service.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("service.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("service.list_services"))

    return render_template("archive-service.html", title="Archive service", service=service, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    service: Service = db.get_or_404(Service, id)
    form: RestoreServiceForm = RestoreServiceForm()

    if form.validate_on_submit() and form.confirm.data is True:
        service.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("service.view", id=service.id)}" class="govuk-notification-banner__link">{service.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("service.list_services"))

    return render_template("restore-service.html", title="Restore service", service=service, form=form)


@bp.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    services: list[Service] = list(
        db.session.execute(db.select(Service).options(selectinload(Service.team)).order_by(Service.name))
        .scalars()
        .all()
    )

    def generate() -> Iterator[str]:
        data = StringIO()
        writer = csv.writer(data, quoting=csv.QUOTE_MINIMAL)

        # Add BOM (Byte Order Mark) for Excel compatibility
        yield "\ufeff"  # This signals that the file is UTF-8 encoded

        # write header
        writer.writerow(("ID", "NAME", "TEAM_ID", "TEAM_NAME", "UPDATED_AT", "ARCHIVED_AT"))
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
