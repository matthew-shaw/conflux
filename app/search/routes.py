from typing import List

from flask import render_template, request, url_for

from app import db
from app.models import Role
from app.search import bp
from app.search.forms import SearchForm


@bp.route("/", methods=["GET"])
def index() -> str:
    """Render the search page."""
    form: SearchForm = SearchForm()
    form.q.data = request.args.get("q", type=str)
    results: List = []

    if form.q.data:
        query: str = f"%{form.q.data.strip()}%"

        # Search Roles
        roles = db.session.execute(db.select(Role).filter(Role.name.ilike(query))).scalars().all()

        # Combine all results into a single list with type info
        for role in roles:
            results.append(
                {
                    "type": "Role",
                    "id": role.id,
                    "name": role.name,
                    "updated_at": role.updated_at,
                    "url": url_for("role.view", id=role.id),
                }
            )

    return render_template("search.html", form=form, results=results)
