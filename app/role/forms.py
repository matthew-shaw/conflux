from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import (
    GovCheckboxInput,
    GovRadioInput,
    GovSubmitInput,
    GovTextInput,
)
from wtforms.fields import BooleanField, RadioField, StringField, SubmitField
from wtforms.validators import InputRequired, ValidationError

from app.models import Role


class RoleForm(FlaskForm):
    name = StringField(
        "Name",
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    grade = RadioField(
        "Grade",
        choices=[],
        widget=GovRadioInput(),
        validators=[InputRequired(message="Select a grade")],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def validate_name(self, field):
        # Check if a role with this name already exists
        if Role.query.filter_by(name=field.data).first():
            raise ValidationError("A role with this name already exists.")


class RoleSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("grade", "Grade"),
            ("updated", "Last updated"),
        ],
        default="name",
    )
    status = RadioField(
        "Status",
        widget=GovRadioInput(),
        choices=[("all", "All"), ("active", "Active"), ("archived", "Archived")],
        default="active",
    )


class ArchiveRoleForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this role")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())


class RestoreRoleForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to restore this role")],
    )
    submit: SubmitField = SubmitField("Restore", widget=GovSubmitInput())
