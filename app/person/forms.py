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
from wtforms.validators import InputRequired, Optional


class PersonForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    location = SelectField(
        "Location",
        widget=GovSelect(),
        default="",
        coerce=str.lower,
        validators=[InputRequired(message="Select a location")],
    )
    role = SelectField(
        "Role",
        widget=GovSelect(),
        default="",
        validators=[InputRequired(message="Select a role")],
    )
    team = SelectField(
        "Team",
        widget=GovSelect(),
        default="",
        validators=[Optional()],
    )
    manager = SelectField(
        "Manager",
        widget=GovSelect(),
        default="",
        validators=[Optional()],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())


class PersonSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("location", "Location"),
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


class ArchivePersonForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this person")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())


class RestorePersonForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to restore this person")],
    )
    submit: SubmitField = SubmitField("Restore", widget=GovSubmitInput())
