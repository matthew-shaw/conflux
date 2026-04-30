from flask import Response, flash, make_response, redirect, render_template, request
from flask.typing import ResponseReturnValue
from flask_wtf.csrf import CSRFError  # type: ignore
from sqlalchemy import func
from werkzeug.exceptions import HTTPException

from app import db, limiter
from app.main import bp
from app.models import Person, Role, Service, Team


@bp.route("/", methods=["GET"])
def index() -> str:
    counts = {
        "roles": db.session.scalar(db.select(func.count()).select_from(Role).where(Role.archived_at.is_(None))),
        "teams": db.session.scalar(db.select(func.count()).select_from(Team).where(Team.archived_at.is_(None))),
        "people": db.session.scalar(db.select(func.count()).select_from(Person).where(Person.archived_at.is_(None))),
        "services": db.session.scalar(
            db.select(func.count()).select_from(Service).where(Service.archived_at.is_(None))
        ),
    }
    return render_template("index.html", counts=counts)


@bp.route("/accessibility", methods=["GET"])
def accessibility() -> str:
    """Render the accessibility statement page."""
    return render_template("accessibility.html")


@bp.route("/cookies", methods=["GET", "POST"])
def cookies() -> str | Response:
    """Render the cookies page."""
    return render_template("cookies.html")


@limiter.exempt
@bp.route("/health", methods=["GET"])
def health() -> ResponseReturnValue:
    """Route for healthchecks"""
    return "OK", 200


@bp.app_errorhandler(HTTPException)
def handle_http_exception(error: HTTPException) -> ResponseReturnValue:
    code: int = error.code or 500
    return render_template(f"{code}.html"), code


@bp.app_errorhandler(CSRFError)
def handle_csrf_error(error: CSRFError) -> ResponseReturnValue:
    """Handle CSRF errors and display a flash message."""
    flash("The form you were submitting has expired. Please try again.")
    return redirect(request.url)
