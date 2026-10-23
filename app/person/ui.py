import csv
import logging
from collections.abc import Iterator
from io import StringIO
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
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app.exceptions import ArchivedEntityError
from app.models import Person, Role, Team
from app.person import ui_bp as ui
from app.person.forms import (
    ArchivePersonForm,
    DeleteGapForm,
    GapForm,
    PersonForm,
    PersonSortFilterForm,
    RestorePersonForm,
)
from app.person.service import (
    archive_person,
    create_gap,
    create_person,
    delete_gap,
    download_people,
    get_active_people,
    get_gap,
    get_people,
    get_person,
    has_matching_gap,
    restore_person,
    update_gap,
    update_person,
)
from app.role.service import get_active_roles
from app.team.service import get_active_teams
from app.utils.pagination import page_out_of_range

logger = logging.getLogger(__name__)


def _needs_fill_gap_choice(form: PersonForm, person: Person | None = None) -> bool:
    """Require an explicit choice when a new or changed assignment matches an open gap.

    A match requires the same employment type, team and role.
    """
    team_id = UUID(form.team.data) if form.team.data else None
    role_id = UUID(form.role.data)
    employment = form.employment.data
    if person is not None and (
        person.archived_at is not None
        or (person.employment, person.team_id, person.role_id) == (employment, team_id, role_id)
    ):
        return False
    if form.fill_gap.data in {"yes", "no"} or not has_matching_gap(employment, team_id, role_id):
        return False
    form.fill_gap.errors = ["Select an answer"]
    return True


def _prepare_leave_gap(form: PersonForm, person: Person) -> bool:
    """Name the person's current role and team in the question and report whether it is offered."""
    if person.team is None or person.archived_at is not None:
        return False
    form.leave_gap.label.text = f"Leave a gap for {person.role.name} in {person.team.name}?"
    return True


def _needs_leave_gap_choice(form: PersonForm, person: Person) -> bool:
    """Require a yes or no answer about leaving a gap when the person changes team."""
    if person.team is None or person.archived_at is not None or form.team.data == f"{person.team_id}":
        return False
    if form.leave_gap.data in {"yes", "no"}:
        return False
    form.leave_gap.errors = ["Select an answer"]
    return True


def _set_profession_filter_choices(form: PersonSortFilterForm) -> None:
    """Populate profession choices from the application configuration."""
    configured_professions = current_app.config.get("PROFESSIONS", [])
    form.profession.choices = [("", "Any")] + [(profession, profession) for profession in configured_professions]


def _set_edit_choices(form: PersonForm) -> None:
    try:
        roles: list[Role] = get_active_roles()
        teams: list[Team] = get_active_teams()
        people: list[Person] = get_active_people()
    except SQLAlchemyError:
        logger.exception("Database error retrieving options for edit person form")
        abort(503)
    form.role.choices = [(role.id, role.name) for role in roles]
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]
    form.manager.choices = [("", "Select a manager")] + [(str(manager.id), manager.display_name) for manager in people]
    form.location.choices = [(location.lower(), location) for location in current_app.config["LOCATIONS"]]


def _populate_person_form(form: PersonForm, person: Person) -> None:
    """Populate editable person details for the initial edit request."""
    name = person.name or ""
    form.name.data = name
    form.email_address.data = person.email_address or (
        f"{name.lower().replace(' ', '.')}@{current_app.config['DOMAIN']}"
    )
    form.location.data = (person.location or "").lower()
    form.employment.data = person.employment
    form.role.data = str(person.role_id)
    form.team.data = str(person.team_id) if person.team_id else ""
    form.manager.data = str(person.manager_id) if person.manager_id else ""


def _set_gap_form_choices(form: GapForm, context: str) -> None:
    """Populate active role and team choices for the gap form."""
    try:
        roles: list[Role] = get_active_roles()
        teams: list[Team] = get_active_teams()
    except SQLAlchemyError:
        logger.exception(f"Database error retrieving options for {context} gap form")
        abort(503)
    form.role.choices = [(str(role.id), role.name) for role in roles]
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]


@ui.route("/", methods=["GET"])
def list_people() -> ResponseReturnValue:
    form: PersonSortFilterForm = PersonSortFilterForm(request.args)
    _set_profession_filter_choices(form)

    page: int = request.args.get("page", 1, type=int)

    try:
        people: Pagination = get_people(
            sort=form.sort.data,
            status=form.status.data,
            employment=form.employment.data,
            page=page,
            per_page=form.per_page.data,
            profession=form.profession.data,
            is_gap={"people": False, "gaps": True}.get(form.kind.data),
        )
        if page_out_of_range(people, page):
            abort(404)
    except SQLAlchemyError:
        logger.exception(
            "Database error listing people "
            f"(sort={form.sort.data},status={form.status.data},employment={form.employment.data},"
            f"profession={form.profession.data},"
            f"page={page},per_page={form.per_page.data})"
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
        roles: list[Role] = get_active_roles()
    except SQLAlchemyError:
        logger.exception("Database error retrieving roles for create person form")
        abort(503)
    form.role.choices = [(str(role.id), role.name) for role in roles]
    try:
        teams: list[Team] = get_active_teams()
    except SQLAlchemyError:
        logger.exception("Database error retrieving teams for create person form")
        abort(503)
    form.team.choices = [("", "Select a team")] + [(str(team.id), team.name) for team in teams]
    try:
        people: list[Person] = get_active_people()
    except SQLAlchemyError:
        logger.exception("Database error retrieving managers for create person form")
        abort(503)
    form.manager.choices = [("", "Select a manager")] + [(str(person.id), person.display_name) for person in people]

    form.location.choices = [(location.lower(), location) for location in current_app.config["LOCATIONS"]]

    if form.validate_on_submit():
        try:
            if _needs_fill_gap_choice(form):
                return render_template("create-person.html", title="Add a new person", form=form)
            person = create_person(
                name=form.name.data,
                email_address=form.email_address.data,
                location=form.location.data,
                employment=form.employment.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
                manager_id=UUID(form.manager.data) if form.manager.data else None,
                fill_gap=form.fill_gap.data == "yes",
            )
            person_url = url_for("person_ui.view", id=person.id)
            flash(
                f'<a href="{person_url}" class="govuk-notification-banner__link">{person.display_name}</a> '
                "has been created",
                "success",
            )
            logger.info(f"Created person id={person.id} name={person.name}")
            return redirect(url_for("person_ui.list_people"))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")
            logger.warning(f"IntegrityError creating person name={form.name.data}", exc_info=True)
            return render_template("create-person.html", title="Add a new person", form=form)
        except SQLAlchemyError:
            logger.exception(f"Database error creating person name={form.name.data}")
            abort(503)
    return render_template("create-person.html", title="Add a new person", form=form)


@ui.route("/gaps/new", methods=["GET", "POST"], endpoint="create_gap")
def create_gap_view() -> ResponseReturnValue:
    """Add a gap with an employment type, role and optional team.

    A `team` query parameter preselects the team, for links from a team page.
    """
    form = GapForm()
    _set_gap_form_choices(form, "create")
    if request.method == "GET" and (team_id := request.args.get("team", "")):
        form.team.data = team_id

    if form.validate_on_submit():
        try:
            gap = create_gap(
                employment=form.employment.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
            )
        except NoResultFound:
            logger.warning("Gap role or team not found while creating gap", exc_info=True)
            abort(404)
        except SQLAlchemyError:
            logger.exception("Database error creating gap")
            abort(503)
        gap_url = url_for("person_ui.view", id=gap.id)
        flash(
            f'<a href="{gap_url}" class="govuk-notification-banner__link">{gap.display_name}</a> has been created',
            "success",
        )
        logger.info(f"Created gap id={gap.id}")
        return redirect(url_for("person_ui.list_people"))
    return render_template("create-gap.html", title="Add a gap", form=form)


@ui.route("/<uuid:id>/delete-gap", methods=["GET", "POST"], endpoint="delete_gap")
def delete_gap_view(id: UUID) -> ResponseReturnValue:
    """Ask for confirmation before permanently removing a gap."""
    try:
        gap: Person = get_gap(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching gap {id} for removal")
        abort(503)
    form = DeleteGapForm()

    if form.validate_on_submit() and form.confirm.data is True:
        display_name = gap.display_name
        try:
            delete_gap(id)
        except NoResultFound:
            abort(404)
        except SQLAlchemyError:
            logger.exception(f"Database error deleting gap {id}")
            abort(503)
        flash(f"{display_name} has been removed", "success")
        logger.info(f"Deleted gap id={id}")
        return redirect(url_for("person_ui.list_people"))

    return render_template("delete-gap.html", title="Remove gap", gap=gap, form=form)


def _edit_gap(gap: Person) -> ResponseReturnValue:
    """Edit only a gap's employment type, role and team; it is never converted to a person."""
    form = GapForm()
    _set_gap_form_choices(form, "edit")

    if request.method == "GET":
        form.employment.data = gap.employment
        form.role.data = str(gap.role_id)
        form.team.data = str(gap.team_id) if gap.team_id else ""
    elif form.validate_on_submit():
        try:
            update_gap(
                id=gap.id,
                employment=form.employment.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
            )
        except NoResultFound:
            logger.warning(f"Gap not found while editing gap {gap.id}", exc_info=True)
            abort(404)
        except SQLAlchemyError:
            logger.exception(f"Database error editing gap {gap.id}")
            abort(503)
        gap_url = url_for("person_ui.view", id=gap.id)
        flash(
            f'<a href="{gap_url}" class="govuk-notification-banner__link">{gap.display_name}</a> has been updated',
            "success",
        )
        logger.info(f"Edited gap id={gap.id}")
        return redirect(url_for("person_ui.list_people"))

    return render_template("edit-gap.html", title="Edit gap", gap=gap, form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error viewing person {id}")
        abort(503)
    return render_template("view-person.html", person=person)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching person {id} for edit")
        abort(503)
    if person.archived_at is not None:
        flash("This person cannot be changed because they have been archived.")
        return redirect(url_for("person_ui.view", id=person.id))
    if person.is_gap:
        return _edit_gap(person)
    return _edit_person(person)


def _edit_person(person: Person) -> ResponseReturnValue:
    """Edit a real person, prompting for gap choices when their assignment changes."""
    id = person.id
    form: PersonForm = PersonForm()
    _set_edit_choices(form)

    show_leave_gap = _prepare_leave_gap(form, person)

    if request.method == "GET":
        _populate_person_form(form, person)
    elif form.validate_on_submit():
        try:
            needs_leave_gap_choice = _needs_leave_gap_choice(form, person)
            needs_fill_gap_choice = _needs_fill_gap_choice(form, person)
            if needs_leave_gap_choice or needs_fill_gap_choice:
                return render_template(
                    "edit-person.html", title="Edit person", person=person, form=form, show_leave_gap=show_leave_gap
                )
            update_person(
                id=id,
                name=form.name.data,
                email_address=form.email_address.data,
                location=form.location.data,
                employment=form.employment.data,
                role_id=UUID(form.role.data),
                team_id=UUID(form.team.data) if form.team.data else None,
                manager_id=UUID(form.manager.data) if form.manager.data else None,
                fill_gap=form.fill_gap.data == "yes",
                leave_previous_gap=form.leave_gap.data == "yes",
            )
            person_url = url_for("person_ui.view", id=person.id)
            flash(
                f'<a href="{person_url}" class="govuk-notification-banner__link">{person.display_name}</a> '
                "has been updated",
                "success",
            )
            logger.info(f"Updated person id={id}")
            return redirect(url_for("person_ui.list_people"))
        except NoResultFound:
            abort(404)
        except ArchivedEntityError:
            logger.warning(f"Attempt to update archived person {id}")
            flash("This person cannot be changed because they have been archived.")
            return redirect(url_for("person_ui.view", id=person.id))
        except IntegrityError:
            form.name.errors.append("A person with this name already exists.")
        except SQLAlchemyError:
            logger.exception(f"Database error updating person {id}")
            abort(503)

    return render_template(
        "edit-person.html",
        title="Edit person",
        person=person,
        form=form,
        show_leave_gap=show_leave_gap,
    )


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching person {id} for archive")
        abort(503)
    if person.is_gap:
        abort(404)
    form: ArchivePersonForm = ArchivePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            archive_person(id)
            person_url = url_for("person_ui.view", id=person.id)
            logger.info(f"Archived person {id}")
            flash(
                f'<a href="{person_url}" class="govuk-notification-banner__link">{person.name}</a> has been archived',
                "success",
            )
            return redirect(url_for("person_ui.list_people"))
        except SQLAlchemyError:
            logger.exception(f"Database error archiving person {id}")
            abort(503)

    return render_template("archive-person.html", title="Archive person", person=person, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    try:
        person: Person = get_person(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching person {id} for restore")
        abort(503)
    if person.is_gap:
        abort(404)
    form: RestorePersonForm = RestorePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            restore_person(id)
            person_url = url_for("person_ui.view", id=person.id)
            logger.info(f"Restored person {id}")
            flash(
                f'<a href="{person_url}" class="govuk-notification-banner__link">{person.name}</a> has been restored',
                "success",
            )
            return redirect(url_for("person_ui.list_people"))
        except SQLAlchemyError:
            logger.exception(f"Database error restoring person {id}")
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
                "EMAIL_ADDRESS",
                "LOCATION",
                "EMPLOYMENT",
                "UPDATED_AT",
                "ARCHIVED_AT",
                "ROLE_ID",
                "ROLE_NAME",
                "TEAM_ID",
                "TEAM_NAME",
                "MANAGER_ID",
                "MANAGER_NAME",
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
                    (person.name or "").title(),
                    (person.email_address or "").lower(),
                    (person.location or "").title(),
                    person.employment.title(),
                    person.updated_at.isoformat().replace("+00:00", "Z"),
                    (person.archived_at.isoformat().replace("+00:00", "Z") if person.archived_at else ""),
                    person.role_id,
                    person.role.name.title() if person.role else "",
                    person.team_id if person.team_id else "",
                    person.team.name.title() if person.team else "",
                    person.manager_id if person.manager_id else "",
                    (person.manager.name or "").title() if person.manager else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="people.csv")
    return response
