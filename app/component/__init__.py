from flask import Blueprint

bp: Blueprint = Blueprint("component", __name__, template_folder="../templates/component", url_prefix="/components")

from app.component import routes  # noqa: E402,F401
