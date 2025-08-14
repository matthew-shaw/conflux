from flask_wtf import FlaskForm  # type: ignore
from govuk_frontend_wtf.wtforms_widgets import GovTextInput  # type: ignore
from wtforms.fields import StringField  # type: ignore


class SearchForm(FlaskForm):
    q: StringField = StringField(
        "Search",
        widget=GovTextInput(),
        description="Search by role, grade, person, location, team, service or component",
    )
