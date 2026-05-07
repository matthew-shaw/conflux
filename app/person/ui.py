import csv
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
    get_people,
    get_person,
    restore_person,
    update_person,
)
from app.role.service import get_roles
from app.team.service import get_teams


@ui.route("/", methods=["GET"])
def list_people() -> ResponseReturnValue:
    form: PersonSortFilterForm = PersonSortFilterForm()
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    people = get_people(
        sort=form.sort.data,
        status=form.status.data,
    )
    return render_template("list-people.html", title="People", people=people, form=form)


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form = PersonForm()

    # Add options
    roles: list[Role] = get_roles()
    form.role.choices = [(str(role.id), role.name) for role in roles]

    teams: list[Team] = get_teams()
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    people: list[Person] = get_people()
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
            return redirect(url_for("person_ui.list_people"))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")
            return render_template("create-person.html", form=form)
    return render_template("create-person.html", title="Add a new person", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    person: Person = get_person(id)
    return render_template("view-person.html", person=person)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    person: Person = get_person(id)
    form: PersonForm = PersonForm()

    # Add options
    roles: list[Role] = get_roles()
    form.role.choices = [(role.id, role.name) for role in roles]

    teams: list[Team] = get_teams()
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]

    people: list[Person] = get_people()
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
            return redirect(url_for("person_ui.list_people"))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")

    return render_template("edit-person.html", title="Edit person", person=person, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    person: Person = get_person(id)
    form: ArchivePersonForm = ArchivePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        archive_person(id)
        flash(
            f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("person_ui.list_people"))

    return render_template("archive-person.html", title="Archive person", person=person, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    person: Person = get_person(id)
    form: RestorePersonForm = RestorePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        restore_person(id)
        flash(
            f'<a href="{url_for("person_ui.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("person_ui.list_people"))

    return render_template("restore-person.html", title="Restore person", person=person, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    people: list[Person] = download_people()

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
