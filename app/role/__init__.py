from flask import Blueprint

ui_bp: Blueprint = Blueprint(
    "role_ui",
    __name__,
    template_folder="../templates/role",
    url_prefix="/roles",
)
api_bp: Blueprint = Blueprint("role_api", __name__, url_prefix="/api/v1/roles")

from app.role import api, ui  # noqa: E402,F401
