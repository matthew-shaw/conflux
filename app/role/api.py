from uuid import UUID

from flask import Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.role import api_bp as api
from app.role.service import get_role, get_roles


@api.route("/", methods=["GET"])
def list_roles() -> Response:
    try:
        roles = get_roles(
            sort=request.args.get("sort", "name", type=str),
            status=request.args.get("status", "active", type=str),
        )
        return jsonify([role.to_dict() for role in roles])
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp


@api.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> Response:
    try:
        role = get_role(id)
        return jsonify(role.to_dict(include_people=True))
    except SQLAlchemyError:
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp
