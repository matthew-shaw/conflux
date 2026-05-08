from uuid import UUID

from flask import Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.models import Team
from app.team import api_bp as api
from app.team.service import get_team, get_teams


@api.route("/", methods=["GET"])
def list_teams() -> Response:
    try:
        teams: list[Team] = get_teams(
            sort=request.args.get("sort", "name", type=str),
            status=request.args.get("status", "active", type=str),
        )
        return jsonify([team.to_dict() for team in teams])
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp


@api.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> Response:
    try:
        team: Team = get_team(id)
        return jsonify(team.to_dict(include_people=True, include_services=True))
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp
