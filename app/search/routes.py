from typing import List

from flask import render_template, url_for

from app import db
from app.models import Role
from app.search import bp
from app.search.forms import SearchForm


@bp.route("/", methods=["GET", "POST"])
def index() -> str:
    """Render the search page."""
    form: SearchForm = SearchForm()
    results: List = []

    if form.validate_on_submit():
        query: str = f"%{form.query.data.strip()}%"

        # Search Roles
        roles = db.session.execute(db.select(Role).filter(Role.name.ilike(query))).scalars().all()

        # Combine all results into a single list with type info
        for role in roles:
            results.append(
                {
                    "type": "Role",
                    "id": role.id,
                    "name": role.name,
                    "url": url_for("role.view", id=role.id),
                }
            )

    return render_template("search.html", form=form, results=results)
