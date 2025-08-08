from flask_wtf import FlaskForm  # type: ignore
from govuk_frontend_wtf.wtforms_widgets import GovSubmitInput, GovTextInput  # type: ignore
from wtforms.fields import StringField, SubmitField  # type: ignore
from wtforms.validators import InputRequired  # type: ignore


class SearchForm(FlaskForm):
    query: StringField = StringField(
        "Query",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a query")],
    )
    submit: SubmitField = SubmitField("Search", widget=GovSubmitInput())
