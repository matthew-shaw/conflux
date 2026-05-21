from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import (
    GovCheckboxInput,
    GovRadioInput,
    GovSelect,
    GovSubmitInput,
    GovTextArea,
    GovTextInput,
)
from wtforms.fields import (
    BooleanField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired, Optional, ValidationError

from app.models import Service


class ServiceForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
        description="The service name must be unique.",
    )
    description = TextAreaField(
        "Description",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextArea(),
        validators=[Optional()],
        description="This field is optional.",
    )
    team = SelectField(
        "Team",
        widget=GovSelect(),
        default="",
        validators=[Optional()],
        description="This field is optional.",
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service

    def validate_name(self, field):
        existing_service = Service.query.filter_by(name=field.data).first()

        if existing_service and (self.service is None or existing_service.id != self.service.id):
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
