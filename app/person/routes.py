import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Iterator
from uuid import UUID

from flask import Response as FlaskResponse
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app import db
from app.models import Person, Role, Team
from app.person import bp
from app.person.forms import (
    ArchivePersonForm,
    PersonForm,
    PersonSortFilterForm,
    RestorePersonForm,
)


@bp.route("/", methods=["GET"])
def list_people() -> ResponseReturnValue:
    form: PersonSortFilterForm = PersonSortFilterForm()
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    # Start the base SELECT statement
    query = db.select(Person)

    # Apply sorting
    sort = form.sort.data or "name"
    if sort == "name":
        query = query.order_by(Person.name)
    elif sort == "location":
        query = query.order_by(Person.location)
    elif sort == "updated":
        query = query.order_by(Person.updated_at.desc())

    # Apply filter based on status
    status = form.status.data or "active"
    if status == "active":
        query = query.where(Person.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Person.archived_at.is_not(None))
    # No filter if status == "all"

    people: list[Person] = list(db.session.execute(query).scalars().all())

    if request.accept_mimetypes.best == "application/json":
        return jsonify([person.to_dict(include_role=True, include_team=True) for person in people])
    return render_template("list-people.html", title="People", people=people, form=form)


@bp.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form = PersonForm()

    # Add options
    roles = db.session.execute(db.select(Role).where(Role.archived_at.is_(None)).order_by(Role.name)).scalars().all()
    form.role.choices.extend((role.id, role.name) for role in roles)

    teams = db.session.execute(db.select(Team).where(Team.archived_at.is_(None)).order_by(Team.name)).scalars().all()
    form.team.choices.extend((team.id, team.name) for team in teams)

    people = (
        db.session.execute(db.select(Person).where(Person.archived_at.is_(None)).order_by(Person.name)).scalars().all()
    )
    form.manager.choices.extend((person.id, person.name) for person in people)

    form.location.choices.extend((location.lower(), location) for location in current_app.config["LOCATIONS"])

    if form.validate_on_submit():
        person: Person = Person(
            name=form.name.data,
            location=form.location.data,
            role_id=form.role.data,
            team_id=form.team.data if form.team.data else None,
            manager_id=form.manager.data if form.manager.data else None,
        )
        db.session.add(person)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been created',
                "success",
            )
            return redirect(url_for("person.list_people"))
        except IntegrityError:
            db.session.rollback()
            return render_template("create-person.html", form=form)
    return render_template("create-person.html", title="Add a new person", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    person = db.get_or_404(Person, id)
    if request.accept_mimetypes.best == "application/json":
        return jsonify(
            person.to_dict(
                include_role=True,
                include_team=True,
                include_manager=True,
                include_reports=True,
            )
        )
    return render_template("view-person.html", person=person)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    person: Person = db.get_or_404(Person, id)
    form: PersonForm = PersonForm()

    # Add options
    roles = db.session.execute(db.select(Role).where(Role.archived_at.is_(None)).order_by(Role.name)).scalars().all()
    form.role.choices.extend((role.id, role.name) for role in roles)

    teams = db.session.execute(db.select(Team).where(Team.archived_at.is_(None)).order_by(Team.name)).scalars().all()
    form.team.choices.extend((team.id, team.name) for team in teams)

    people = (
        db.session.execute(db.select(Person).where(Person.archived_at.is_(None)).order_by(Person.name)).scalars().all()
    )
    form.manager.choices.extend((person.id, person.name) for person in people)

    form.location.choices.extend((location.lower(), location) for location in current_app.config["LOCATIONS"])

    if request.method == "GET":
        form.name.data = person.name
        form.location.data = person.location.lower()
        form.role.data = str(person.role_id)
        form.team.data = str(person.team_id)
        form.manager.data = str(person.manager_id)
    elif form.validate_on_submit():
        person.name = form.name.data
        person.location = form.location.data
        person.role_id = form.role.data
        person.team_id = form.team.data if form.team.data else None
        person.manager_id = form.manager.data if form.manager.data else None
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("person.list_people"))
        except IntegrityError:
            db.session.rollback()

    return render_template("edit-person.html", title="Edit person", person=person, form=form)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    person: Person = db.get_or_404(Person, id)
    form: ArchivePersonForm = ArchivePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        person.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("person.list_people"))

    return render_template("archive-person.html", title="Archive person", person=person, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    person: Person = db.get_or_404(Person, id)
    form: RestorePersonForm = RestorePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        person.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("person.list_people"))

    return render_template("restore-person.html", title="Restore person", person=person, form=form)


@bp.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    people: list[Person] = list(
        db.session.execute(
            db.select(Person)
            .options(
                selectinload(Person.role),
                selectinload(Person.team),
                selectinload(Person.manager),
            )
            .order_by(Person.name)
        ).scalars()
    )

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
