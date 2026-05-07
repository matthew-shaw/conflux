from flask import Blueprint

ui_bp: Blueprint = Blueprint("team_ui", __name__, template_folder="../templates/team", url_prefix="/teams")
api_bp: Blueprint = Blueprint("team_api", __name__, url_prefix="/api/v1/teams")

from app.team import api, ui  # noqa: E402,F401
