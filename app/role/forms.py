from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import (
    GovCheckboxInput,
    GovSubmitInput,
    GovTextInput,
)
from wtforms.fields import BooleanField, StringField, SubmitField
from wtforms.validators import InputRequired, ValidationError

from app.models import Role


class RoleForm(FlaskForm):
    name = StringField(
        "Name",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def validate_name(self, field):
        # Check if a role with this name already exists
        if Role.query.filter_by(name=field.data).first():
            raise ValidationError("A role with this name already exists.")


class ArchiveRoleForm(FlaskForm):
    confirm = BooleanField(
        "Confirm",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this role")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())
