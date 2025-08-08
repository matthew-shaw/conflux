from flask import Blueprint

bp: Blueprint = Blueprint("search", __name__, template_folder="../templates/search", url_prefix="/search")

from app.search import routes  # noqa: E402,F401
