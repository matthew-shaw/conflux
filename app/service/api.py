import logging
from uuid import UUID

from flask import Response, jsonify, request
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from app.service import api_bp as api
from app.service.service import get_service, get_services
from app.utils.pagination import page_out_of_range

logger = logging.getLogger(__name__)


@api.route("/", methods=["GET"])
def list_services() -> Response:
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        services = get_services(
            sort=request.args.get("sort", "name", type=str),
            status=request.args.get("status", "active", type=str),
            page=page,
            per_page=per_page,
        )

        if page_out_of_range(services, page):
            logger.warning(f"Page out of range listing services page={page} per_page={per_page}")
            resp = jsonify({"error": "Page not found"})
            resp.status_code = 404
            return resp

        return jsonify([service.to_dict() for service in services])
    except SQLAlchemyError:
        logger.exception("Database error listing services")
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp


@api.route("/<uuid:id>", methods=["GET"])
def view(id: UUID) -> Response:
    try:
        service = get_service(id)
        return jsonify(
            service.to_dict(
                include_team=True,
            )
        )
    except NoResultFound:
        logger.warning(f"Service not found {id}")
        resp = jsonify({"error": "Service not found"})
        resp.status_code = 404
        return resp
    except SQLAlchemyError:
        logger.exception(f"Database error viewing service {id}")
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp
