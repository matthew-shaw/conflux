from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import GovSubmitInput, GovTextInput
from wtforms.fields import StringField, SubmitField
from wtforms.validators import InputRequired


class RoleForm(FlaskForm):
    title = StringField(
        "Title",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter the title")],
    )
    save: SubmitField = SubmitField("Save", widget=GovSubmitInput())
