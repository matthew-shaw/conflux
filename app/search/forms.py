from flask_wtf import FlaskForm  # type: ignore
from govuk_frontend_wtf.wtforms_widgets import GovRadioInput, GovSubmitInput, GovTextInput  # type: ignore
from wtforms.fields import RadioField, StringField, SubmitField  # type: ignore
from wtforms.validators import InputRequired  # type: ignore


class SearchForm(FlaskForm):
    query: StringField = StringField(
        "Query",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a query")],
    )
    type: RadioField = RadioField(
        "Type",
        widget=GovRadioInput(),
        validators=[InputRequired(message="Select a type")],
        choices=[
            ("roles", "Roles"),
            ("people", "People"),
            ("teams", "Teams"),
            ("services", "Services"),
            ("components", "Components"),
        ],
    )
    submit: SubmitField = SubmitField("Search", widget=GovSubmitInput())
