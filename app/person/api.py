from uuid import UUID

from flask import Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.person import api_bp as api
from app.person.service import get_people, get_person


@api.route("/", methods=["GET"])
def list_people() -> Response:
    try:
        people = get_people(
            sort=request.args.get("sort", "name", type=str),
            status=request.args.get("status", "active", type=str),
        )
        return jsonify([person.to_dict() for person in people])
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp


@api.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> Response:
    try:
        person = get_person(id)
        return jsonify(
            person.to_dict(
                include_manager=True,
                include_reports=True,
                include_role=True,
                include_team=True,
            )
        )
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp
