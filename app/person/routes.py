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
from app.models import Person, Role, Team
from app.person import bp
from app.person.forms import (
    ArchivePersonForm,
    PersonForm,
    PersonSortFilterForm,
    RestorePersonForm,
)


@bp.route("/", methods=["GET"])
def list() -> str:
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

    people: List[Person] = db.session.execute(query).scalars().all()

    return render_template("list-people.html", title="People", people=people, form=form)


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    form: PersonForm = PersonForm()
    roles = db.session.execute(db.select(Role).order_by(Role.name)).scalars().all()
    teams = db.session.execute(db.select(Team).order_by(Team.name)).scalars().all()
    form.role.choices = [(role.id, role.name) for role in roles]
    form.team.choices = [(team.id, team.name) for team in teams]
    form.location.choices = [(location, location) for location in current_app.config["LOCATIONS"]]

    if form.validate_on_submit():
        person: Person = Person(
            name=form.name.data,
            location=form.location.data,
            role_id=form.role.data,
            team_id=form.team.data,
        )
        db.session.add(person)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been created',
                "success",
            )
            return redirect(url_for("person.list"))
        except IntegrityError:
            db.session.rollback()
            return render_template("create-person.html", form=form)
    return render_template("create-person.html", title="Add a new person", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> str:
    person = db.get_or_404(Person, id)
    return render_template("view-person.html", person=person)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> str:
    person: Person = db.get_or_404(Person, id)
    form: PersonForm = PersonForm()
    roles = db.session.execute(db.select(Role).order_by(Role.name)).scalars().all()
    teams = db.session.execute(db.select(Team).order_by(Team.name)).scalars().all()
    form.role.choices = [(role.id, role.name) for role in roles]
    form.team.choices = [(team.id, team.name) for team in teams]
    form.location.choices = [(location, location) for location in current_app.config["LOCATIONS"]]

    if request.method == "GET":
        form.name.data = person.name
        form.location.data = person.location
        form.role.data = str(person.role_id)
        form.team.data = str(person.team_id)
    elif form.validate_on_submit():
        person.name = form.name.data
        person.location = form.location.data
        person.role_id = form.role.data
        person.team_id = form.team.data
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("person.list"))
        except IntegrityError:
            db.session.rollback()

    return render_template("edit-person.html", title="Edit person", person=person, form=form)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> str:
    person: Person = db.get_or_404(Person, id)
    form: ArchivePersonForm = ArchivePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        person.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("person.list"))

    return render_template("archive-person.html", title="Archive person", person=person, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> str:
    person: Person = db.get_or_404(Person, id)
    form: RestorePersonForm = RestorePersonForm()

    if form.validate_on_submit() and form.confirm.data is True:
        person.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("person.view", id=person.id)}" class="govuk-notification-banner__link">{person.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("person.list"))

    return render_template("restore-person.html", title="Restore person", person=person, form=form)


@bp.route("/download", methods=["GET"])
def download():
    people: List[Person] = db.session.execute(db.select(Person).order_by(Person.name)).scalars().all()

    def generate():
        data = StringIO()
        writer = csv.writer(data, quoting=csv.QUOTE_MINIMAL)

        # Add BOM (Byte Order Mark) for Excel compatibility
        yield "\ufeff"  # This signals that the file is UTF-8 encoded

        # write header
        writer.writerow(
            (
                "ID",
                "NAME",
                "LOCATION",
                "ROLE_ID",
                "TEAM_ID",
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
                    person.location,
                    person.role_id,
                    person.team_id,
                    person.updated_at.isoformat(),
                    person.archived_at.isoformat() if person.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response = Response(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="people.csv")
    return response
