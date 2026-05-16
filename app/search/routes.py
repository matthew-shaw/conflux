from flask import abort, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.search import bp
from app.search.forms import SearchForm
from app.search.service import search_entries


@bp.route("/", methods=["GET"])
def index() -> str:
    """Render the search page."""
    form: SearchForm = SearchForm()
    form.q.data = request.args.get("q", type=str)
    results: list[dict[str, object]] = []

    if form.q.data:
        try:
            results = search_entries(form.q.data)
        except SQLAlchemyError:
            abort(503)

        for item in results:
            if item["type"] == "Role":
                item["url"] = url_for("role_ui.view", id=item["id"])
            elif item["type"] == "Person":
                item["url"] = url_for("person_ui.view", id=item["id"])
            elif item["type"] == "Team":
                item["url"] = url_for("team_ui.view", id=item["id"])
            elif item["type"] == "Service":
                item["url"] = url_for("service_ui.view", id=item["id"])

    return render_template("search.html", form=form, results=results)
