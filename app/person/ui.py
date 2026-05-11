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

from app.models import Person, Role, Team
from app.person import ui_bp as ui
from app.person.forms import (
    ArchivePersonForm,
    PersonForm,
    PersonSortFilterForm,
    RestorePersonForm,
)
from app.person.service import (
    archive_person,
    create_person,
    download_people,
    get_active_people,
    get_people,
    get_person,
    restore_person,
    update_person,
)
from app.role.service import get_roles
from app.team.service import get_teams

logger = logging.getLogger(__name__)


@ui.route("/", methods=["GET"])
def list_people() -> ResponseReturnValue:
    form: PersonSortFilterForm = PersonSortFilterForm(request.args)

    page: int = request.args.get("page", 1, type=int)

    try:
        people: Pagination = get_people(
            sort=form.sort.data,
            status=form.status.data,
            page=page,
            per_page=form.per_page.data,
        )
    except SQLAlchemyError:
        logger.exception(
            f"Database error listing people (sort={form.sort.data},status={form.status.data},page={page},per_page={form.per_page.data})"
        )
        abort(503)

    return render_template(
        "list-people.html",
        title="People",
        people=people,
        form=form,
    )


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form = PersonForm()

    # Add options
    try:
        roles: list[Role] = get_roles()
    except SQLAlchemyError:
        logger.exception("Database error retrieving roles for create person form")
        abort(503)
    form.role.choices = [(str(role.id), role.name) for role in roles]
    try:
        teams: list[Team] = get_teams()
    except SQLAlchemyError:
        logger.exception("Database error retrieving teams for create person form")
        abort(503)
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]
    try:
        people: list[Person] = get_active_people()
    except SQLAlchemyError:
        logger.exception("Database error retrieving managers for create person form")
        abort(503)
    form.manager.choices = [("", "Select a manager")] + [(str(person.id), person.name) for person in people]

    form.location.choices = [(location.lower(), location) for location in current_app.config["LOCATIONS"]]

    if form.validate_on_submit():
        try:
            person = create_person(
                name=form.name.data,
                email_address=form.email_address.data,
                location=form.location.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
                manager_id=UUID(form.manager.data) if form.manager.data else None,
            )
            flash(
                f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been created',
                "success",
            )
            logger.info("Created person id=%s name=%s", person.id, person.name)
            return redirect(url_for("person_ui.list_people"))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")
            logger.warning("IntegrityError creating person name=%s", form.name.data, exc_info=True)
            return render_template("create-person.html", form=form)
        except SQLAlchemyError:
            logger.exception("Database error creating person name=%s", form.name.data)
            abort(503)
    return render_template("create-person.html", title="Add a new person", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except SQLAlchemyError:
        logger.exception("Database error viewing person %s", id)
        abort(503)
    return render_template("view-person.html", person=person)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching person %s for edit", id)
        abort(503)
    form: PersonForm = PersonForm()

    # Add options
    try:
        roles: list[Role] = get_roles()
    except SQLAlchemyError:
        logger.exception("Database error retrieving roles for edit person form")
        abort(503)
    form.role.choices = [(role.id, role.name) for role in roles]
    try:
        teams: list[Team] = get_teams()
    except SQLAlchemyError:
        logger.exception("Database error retrieving teams for edit person form")
        abort(503)
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]
    try:
        people: list[Person] = get_active_people()
    except SQLAlchemyError:
        logger.exception("Database error retrieving managers for edit person form")
        abort(503)
    form.manager.choices = [("", "Select a manager")] + [(str(person.id), person.name) for person in people]

    form.location.choices = [(location.lower(), location) for location in current_app.config["LOCATIONS"]]

    if request.method == "GET":
        form.name.data = person.name
        if person.email_address:
            form.email_address.data = person.email_address
        else:
            form.email_address.data = person.name.lower().replace(" ", ".") + "@" + current_app.config["DOMAIN"]
        form.location.data = person.location.lower()
        form.role.data = str(person.role_id)
        form.team.data = str(person.team_id)
        form.manager.data = str(person.manager_id)
    elif form.validate_on_submit():
        try:
            update_person(
                id=id,
                name=form.name.data,
                email_address=form.email_address.data,
                location=form.location.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
                manager_id=UUID(form.manager.data) if form.manager.data else None,
            )
            flash(
                f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been updated',
                "success",
            )
            logger.info("Updated person id=%s", id)
            return redirect(url_for("person_ui.list_people"))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")
        except SQLAlchemyError:
            logger.exception("Database error updating person %s", id)
            abort(503)

    return render_template("edit-person.html", title="Edit person", person=person, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching person %s for archive", id)
        abort(503)
    form: ArchivePersonForm = ArchivePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            archive_person(id)
            logger.info("Archived person %s", id)
            flash(
                f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been archived',
                "success",
            )
            return redirect(url_for("person_ui.list_people"))
        except SQLAlchemyError:
            logger.exception("Database error archiving person %s", id)
            abort(503)

    return render_template("archive-person.html", title="Archive person", person=person, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except SQLAlchemyError:
        logger.exception("Database error fetching person %s for restore", id)
        abort(503)
    form: RestorePersonForm = RestorePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            restore_person(id)
            logger.info("Restored person %s", id)
            flash(
                f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been restored',
                "success",
            )
            return redirect(url_for("person_ui.list_people"))
        except SQLAlchemyError:
            logger.exception("Database error restoring person %s", id)
            abort(503)

    return render_template("restore-person.html", title="Restore person", person=person, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    try:
        people: list[Person] = download_people()
    except SQLAlchemyError:
        logger.exception("Database error downloading people")
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
                "ROLE_ID",
                "ROLE_NAME",
                "TEAM_ID",
                "TEAM_NAME",
                "LOCATION",
                "MANAGER_ID",
                "MANAGER_NAME",
                "UPDATED_AT",
                "ARCHIVED_AT",
            )
        )
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        for person in people:
            writer.writerow(
                (
                    person.id,
                    person.name,
                    person.role.id if person.role else "",
                    person.role.name if person.role else "",
                    person.team.id if person.team else "",
                    person.team.name if person.team else "",
                    person.location.title(),
                    person.manager.id if person.manager else "",
                    person.manager.name if person.manager else "",
                    person.updated_at.isoformat(),
                    person.archived_at.isoformat() if person.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="people.csv")
    return response
