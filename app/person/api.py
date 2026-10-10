import logging
from uuid import UUID

from flask import Response, jsonify, request
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from app.person import api_bp as api
from app.person.service import get_people, get_person
from app.utils.pagination import page_out_of_range

logger = logging.getLogger(__name__)


@api.route("/", methods=["GET"])
def list_people() -> Response:
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        people = get_people(
            sort=request.args.get("sort", "name", type=str),
            status=request.args.get("status", "active", type=str),
            employment_type=request.args.get("employment_type", "all", type=str),
            page=page,
            per_page=per_page,
            profession=request.args.get("profession", "", type=str),
        )

        if page_out_of_range(people, page):
            logger.warning(f"Page out of range listing people page={page} per_page={per_page}")
            resp = jsonify({"error": "Page not found"})
            resp.status_code = 404
            return resp

        return jsonify([person.to_dict() for person in people])
    except SQLAlchemyError:
        logger.exception("Database error listing people")
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
    except NoResultFound:
        logger.warning(f"Person not found {id}")
        resp = jsonify({"error": "Person not found"})
        resp.status_code = 404
        return resp
    except SQLAlchemyError:
        logger.exception(f"Database error viewing person {id}")
        resp = jsonify({"error": "Database error"})
        resp.status_code = 503
        return resp
