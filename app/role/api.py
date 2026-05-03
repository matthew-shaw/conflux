from uuid import UUID

from flask import Response, jsonify, request

from app.role import api_bp as api
from app.role.service import get_role, get_roles


@api.route("/", methods=["GET"])
def list_roles() -> Response:
    roles = get_roles(
        sort=request.args.get("sort", "name", type=str),
        status=request.args.get("status", "active", type=str),
    )
    return jsonify([role.to_dict() for role in roles])


@api.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> Response:
    role = get_role(id)
    return jsonify(role.to_dict())
