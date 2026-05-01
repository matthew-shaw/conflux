from flask_wtf import FlaskForm  # type: ignore
from govuk_frontend_wtf.wtforms_widgets import GovTextInput  # type: ignore
from wtforms.fields import StringField  # type: ignore


class SearchForm(FlaskForm):
    q: StringField = StringField(
        "Search",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        description="Search by role, grade, person, location, team, or service",
    )
