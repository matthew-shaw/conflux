from flask import Blueprint

ui_bp: Blueprint = Blueprint(
    "service_ui",
    __name__,
    template_folder="../templates/service",
    url_prefix="/services",
)
api_bp: Blueprint = Blueprint("service_api", __name__, url_prefix="/api/v1/services")

from app.service import api, ui  # noqa: E402,F401
