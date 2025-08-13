from typing import List

from flask import render_template, request, url_for
from sqlalchemy import or_

from app import db
from app.models import Person, Role, Team
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
        roles = (
            db.session.execute(db.select(Role).filter(or_(Role.name.ilike(query), Role.grade.ilike(query))))
            .scalars()
            .all()
        )

        # Search People
        people = db.session.execute(db.select(Person).filter(Person.name.ilike(query))).scalars().all()

        # Search Teams
        teams = db.session.execute(db.select(Team).filter(Team.name.ilike(query))).scalars().all()

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

        for person in people:
            results.append(
                {
                    "type": "Person",
                    "id": person.id,
                    "name": person.name,
                    "updated_at": person.updated_at,
                    "url": url_for("person.view", id=person.id),
                }
            )

        for team in teams:
            results.append(
                {
                    "type": "Team",
                    "id": team.id,
                    "name": team.name,
                    "updated_at": team.updated_at,
                    "url": url_for("team.view", id=team.id),
                }
            )

        # Sort results alphabetically by name (case-insensitive)
        results.sort(key=lambda r: r["name"].lower())

    return render_template("search.html", form=form, results=results)
