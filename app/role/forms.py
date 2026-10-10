from flask import current_app
from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import (
    GovCheckboxInput,
    GovRadioInput,
    GovSelect,
    GovSubmitInput,
    GovTextInput,
)
from wtforms.fields import (
    BooleanField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import InputRequired, Optional, ValidationError

from app.models import Role


class RoleForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
        description="The role name must be unique.",
    )
    grade = RadioField(
        "Grade",
        choices=[],
        widget=GovRadioInput(),
        validators=[InputRequired(message="Select a grade")],
    )
    profession = SelectField(
        "Profession",
        choices=[("", "None")],
        widget=GovSelect(),
        default="",
        validators=[Optional()],
        description="This field is optional.",
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role

    def validate_name(self, field):
        existing_role = Role.query.filter_by(name=field.data).first()

        if existing_role and (self.role is None or existing_role.id != self.role.id):
            raise ValidationError("A role with this name already exists.")

    def validate_profession(self, field):
        configured_professions = current_app.config.get("PROFESSIONS", [])
        current_profession = self.role.profession if self.role else None

        if field.data and field.data not in configured_professions and field.data != current_profession:
            raise ValidationError("Select a valid profession")


class RoleSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("grade", "Grade"),
            ("updated", "Updated"),
        ],
        default="name",
    )
    status = RadioField(
        "Status",
        widget=GovRadioInput(),
        choices=[("all", "All"), ("active", "Active"), ("archived", "Archived")],
        default="active",
    )
    profession = SelectField(
        "Profession",
        widget=GovSelect(),
        choices=[("", "Any")],
        default="",
        validators=[Optional()],
    )
    per_page = SelectField(
        "Items per page",
        widget=GovSelect(),
        choices=[
            (10, "10"),
            (25, "25"),
            (50, "50"),
        ],
        default=25,
        coerce=int,
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
