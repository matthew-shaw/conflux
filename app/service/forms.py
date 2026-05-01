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

from app.models import Service


class ServiceForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    team = SelectField(
        "Team",
        choices=[("", "Select a team")],
        widget=GovSelect(),
        default="",
        validators=[Optional()],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def validate_name(self, field):
        # Check if a service with this name already exists
        if Service.query.filter_by(name=field.data).first():
            raise ValidationError("A service with this name already exists.")


class ServiceSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
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


class ArchiveServiceForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this service")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())


class RestoreServiceForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to restore this service")],
    )
    submit: SubmitField = SubmitField("Restore", widget=GovSubmitInput())
