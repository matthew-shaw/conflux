from flask import Blueprint

bp: Blueprint = Blueprint("person", __name__, template_folder="../templates/person", url_prefix="/people")

from app.person import routes  # noqa: E402,F401
