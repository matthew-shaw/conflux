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
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app.models import Team
from app.team import ui_bp as ui
from app.team.forms import (
    ArchiveTeamForm,
    RestoreTeamForm,
    TeamForm,
    TeamSortFilterForm,
)
from app.team.service import (
    archive_team,
    create_team,
    download_teams,
    get_team,
    get_teams,
    restore_team,
    update_team,
)

logger = logging.getLogger(__name__)


@ui.route("/", methods=["GET"])
def list_teams() -> ResponseReturnValue:
    form: TeamSortFilterForm = TeamSortFilterForm(request.args)

    page: int = request.args.get("page", 1, type=int)

    try:
        teams: Pagination = get_teams(
            sort=form.sort.data,
            status=form.status.data,
            page=page,
            per_page=form.per_page.data,
        )
    except SQLAlchemyError:
        logger.exception(
            "Database error listing teams "
            f"(sort={form.sort.data},status={form.status.data},"
            f"page={page},per_page={form.per_page.data})"
        )
        abort(503)

    return render_template(
        "list-teams.html",
        title="Teams",
        teams=teams,
        form=form,
    )


@ui.route("/new", methods=["GET", "POST"])
def create() -> ResponseReturnValue:
    form: TeamForm = TeamForm()

    if form.validate_on_submit():
        try:
            team = create_team(
                name=form.name.data,
            )
            team_url = url_for("team_ui.view", id=team.id)
            flash(
                f'<a href="{team_url}" class="govuk-notification-banner__link">{team.name}</a> has been created',
                "success",
            )
            logger.info(f"Created team id={team.id} name={team.name}")
            return redirect(url_for("team_ui.list_teams"))
        except IntegrityError:
            form.name.errors.append("A team with this name already exists.")
            logger.warning(f"IntegrityError creating team name={form.name.data}", exc_info=True)
            return render_template("create-team.html", form=form)
        except SQLAlchemyError:
            logger.exception(f"Database error creating team name={form.name.data}")
            abort(503)
    return render_template("create-team.html", title="Add a new team", form=form)


@ui.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> ResponseReturnValue:
    try:
        team: Team = get_team(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error viewing team {id}")
        abort(503)
    return render_template("view-team.html", team=team)


@ui.route("/<uuid:id>/edit", methods=["GET", "POST"])
def edit(id: UUID) -> ResponseReturnValue:
    try:
        team: Team = get_team(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching team {id} for edit")
        abort(503)
    form: TeamForm = TeamForm(team=team)

    if request.method == "GET":
        form.name.data = team.name
    elif form.validate_on_submit():
        try:
            update_team(
                id=id,
                name=form.name.data,
            )
            team_url = url_for("team_ui.view", id=team.id)
            flash(
                f'<a href="{team_url}" class="govuk-notification-banner__link">{team.name}</a> has been updated',
                "success",
            )
            logger.info(f"Updated team id={team.id} name={form.name.data}")
            return redirect(url_for("team_ui.list_teams"))
        except IntegrityError:
            form.name.errors.append("A team with this name already exists.")
            logger.warning(
                f"IntegrityError updating team id={id} name={form.name.data}",
                exc_info=True,
            )
        except SQLAlchemyError:
            logger.exception(f"Database error updating team {id}")
            abort(503)

    return render_template("edit-team.html", title="Edit team", team=team, form=form)


@ui.route("/<uuid:id>/archive", methods=["GET", "POST"])
def archive(id: UUID) -> ResponseReturnValue:
    try:
        team: Team = get_team(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching team for archive {id}")
        abort(503)
    form: ArchiveTeamForm = ArchiveTeamForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            archive_team(id)
            logger.info(f"Archived team {id}")
            team_url = url_for("team_ui.view", id=team.id)
            flash(
                f'<a href="{team_url}" class="govuk-notification-banner__link">{team.name}</a> has been archived',
                "success",
            )
            return redirect(url_for("team_ui.list_teams"))
        except SQLAlchemyError:
            logger.exception(f"Database error archiving team {id}")
            abort(503)

    return render_template("archive-team.html", title="Archive team", team=team, form=form)


@ui.route("/<uuid:id>/restore", methods=["GET", "POST"])
def restore(id: UUID) -> ResponseReturnValue:
    try:
        team: Team = get_team(id)
    except NoResultFound:
        abort(404)
    except SQLAlchemyError:
        logger.exception(f"Database error fetching team for restore {id}")
        abort(503)
    form: RestoreTeamForm = RestoreTeamForm()

    if form.validate_on_submit() and form.confirm.data is True:
        try:
            restore_team(id)
            logger.info(f"Restored team {id}")
            team_url = url_for("team_ui.view", id=team.id)
            flash(
                f'<a href="{team_url}" class="govuk-notification-banner__link">{team.name}</a> has been restored',
                "success",
            )
            return redirect(url_for("team_ui.list_teams"))
        except SQLAlchemyError:
            logger.exception(f"Database error restoring team {id}")
            abort(503)

    return render_template("restore-team.html", title="Restore team", team=team, form=form)


@ui.route("/download", methods=["GET"])
def download() -> ResponseReturnValue:
    try:
        teams: list[Team] = download_teams()
    except SQLAlchemyError:
        logger.exception("Database error downloading teams")
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
                "UPDATED_AT",
                "ARCHIVED_AT",
            )
        )
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        for team in teams:
            writer.writerow(
                (
                    team.id,
                    team.name,
                    team.updated_at.isoformat().replace("+00:00", "Z"),
                    team.archived_at.isoformat().replace("+00:00", "Z") if team.archived_at else "",
                )
            )
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response: FlaskResponse = FlaskResponse(generate(), mimetype="text/csv", status=200)
    response.headers.set("Content-Disposition", "attachment", filename="teams.csv")
    return response
