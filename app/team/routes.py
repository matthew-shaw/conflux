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

from app import db
from app.models import Team
from app.team import bp
from app.team.forms import (
    ArchiveTeamForm,
    RestoreTeamForm,
    TeamForm,
    TeamSortFilterForm,
)


@bp.route("/", methods=["GET"])
def list_teams() -> ResponseReturnValue:
    form: TeamSortFilterForm = TeamSortFilterForm()
    form.sort.data = request.args.get("sort", "name", type=str)
    form.status.data = request.args.get("status", "active", type=str)

    # Start the base SELECT statement
    query = db.select(Team)

    # Apply sorting
    sort = form.sort.data or "name"
    if sort == "name":
        query = query.order_by(Team.name)
    elif sort == "updated":
        query = query.order_by(Team.updated_at.desc())

    # Apply filter based on status
    status = form.status.data or "active"
    if status == "active":
        query = query.where(Team.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Team.archived_at.is_not(None))
    # No filter if status == "all"

    teams: list[Team] = list(db.session.execute(query).scalars().all())

    return render_template("list-teams.html", title="Teams", teams=teams, form=form)


@bp.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form: TeamForm = TeamForm()
    if form.validate_on_submit():
        team: Team = Team(name=form.name.data)
        db.session.add(team)
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("team.view", id=team.id)}" class="govuk-notification-banner__link">{team.name}</a> has been created',
                "success",
            )
            return redirect(url_for("team.list_teams"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A team with this name already exists.")
            return render_template("create-team.html", form=form)
    return render_template("create-team.html", title="Add a new team", form=form)


@bp.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    team = db.get_or_404(Team, id)
    return render_template("view-team.html", team=team)


@bp.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    team: Team = db.get_or_404(Team, id)
    form: TeamForm = TeamForm()

    if request.method == "GET":
        form.name.data = team.name
    elif form.validate_on_submit():
        team.name = form.name.data
        try:
            db.session.commit()
            flash(
                f'<a href="{url_for("team.view", id=team.id)}" class="govuk-notification-banner__link">{team.name}</a> has been updated',
                "success",
            )
            return redirect(url_for("team.list_teams"))
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("A team with this name already exists.")

    return render_template("edit-team.html", title="Edit team", team=team, form=form)


@bp.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    team: Team = db.get_or_404(Team, id)
    form: ArchiveTeamForm = ArchiveTeamForm()

    if form.validate_on_submit() and form.confirm.data is True:
        team.archived_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(
            f'<a href="{url_for("team.view", id=team.id)}" class="govuk-notification-banner__link">{team.name}</a> has been archived',
            "success",
        )
        return redirect(url_for("team.list_teams"))

    return render_template("archive-team.html", title="Archive team", team=team, form=form)


@bp.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    team: Team = db.get_or_404(Team, id)
    form: RestoreTeamForm = RestoreTeamForm()

    if form.validate_on_submit() and form.confirm.data is True:
        team.archived_at = None
        db.session.commit()
        flash(
            f'<a href="{url_for("team.view", id=team.id)}" class="govuk-notification-banner__link">{team.name}</a> has been restored',
            "success",
        )
        return redirect(url_for("team.list_teams"))

    return render_template("restore-team.html", title="Restore team", team=team, form=form)


@bp.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    teams: list[Team] = list(db.session.execute(db.select(Team).order_by(Team.name)).scalars().all())

    def generate() -> Iterator[str]:
        data = StringIO()
        writer = csv.writer(data, quoting=csv.QUOTE_MINIMAL)

        # Add BOM (Byte Order Mark) for Excel compatibility
        yield "\ufeff"  # This signals that the file is UTF-8 encoded

        # write header
        writer.writerow(("ID", "NAME", "UPDATED_AT", "ARCHIVED_AT"))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        for team in teams:
            writer.writerow(
                (
                    team.id,
                    team.name,
                    team.updated_at.isoformat(),
                    team.archived_at.isoformat() if team.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="teams.csv")
    return response
