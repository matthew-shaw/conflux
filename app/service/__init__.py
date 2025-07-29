from flask import Blueprint

bp: Blueprint = Blueprint("service", __name__, template_folder="../templates/service", url_prefix="/services")

from app.service import routes  # noqa: E402,F401
