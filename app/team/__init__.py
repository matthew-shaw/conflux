from flask import Blueprint

bp: Blueprint = Blueprint("team", __name__, template_folder="../templates/team", url_prefix="/teams")

from app.team import routes  # noqa: E402,F401
