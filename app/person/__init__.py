from flask import Blueprint

ui_bp: Blueprint = Blueprint("person_ui", __name__, template_folder="../templates/person", url_prefix="/people")
api_bp: Blueprint = Blueprint("person_api", __name__, url_prefix="/api/v1/people")

from app.person import api, ui  # noqa: E402,F401
