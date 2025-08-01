from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import GovSubmitInput, GovTextInput
from wtforms.fields import StringField, SubmitField
from wtforms.validators import InputRequired, ValidationError

from app.models import Role


class RoleForm(FlaskForm):
    title = StringField(
        "Title",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter the title")],
    )
    save: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def validate_title(self, field):
        # Check if a role with this title already exists
        if Role.query.filter_by(title=field.data).first():
            raise ValidationError("A role with this title already exists.")
