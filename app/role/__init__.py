from flask import Blueprint

bp: Blueprint = Blueprint("role", __name__, template_folder="../templates/role", url_prefix="/roles")

from app.role import routes  # noqa: E402,F401
