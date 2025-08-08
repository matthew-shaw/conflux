from flask import render_template

from app.search import bp
from app.search.forms import SearchForm


@bp.route("/", methods=["GET", "POST"])
def index() -> str:
    """Render the search page."""
    form: SearchForm = SearchForm()

    if form.validate_on_submit():
        pass
    return render_template("search.html", form=form)
