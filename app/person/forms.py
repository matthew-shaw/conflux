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
from wtforms.validators import Email, InputRequired, Length, Optional


class PersonForm(FlaskForm):
    name = StringField(
        "Full name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    email_address = StringField(
        "Email address",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[
            InputRequired(message="Enter an email address"),
            Length(max=254, message="Email address must be 254 characters or fewer"),
            Email(message="Enter an email address in the correct format, like name@example.com"),
        ],
        description="The email address must be unique.",
    )
    location = SelectField(
        "Location",
        widget=GovSelect(),
        default="",
        coerce=str.lower,
        validators=[InputRequired(message="Select a location")],
        description="The person's assigned office location.",
    )
    employment = SelectField(
        "Employment type",
        widget=GovSelect(),
        choices=[("employee", "Employee"), ("contractor", "Contractor")],
        validators=[InputRequired(message="Select an employment type")],
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
        description="This field is optional.",
    )
    manager = SelectField(
        "Manager",
        widget=GovSelect(),
        default="",
        validators=[Optional()],
        description="This field is optional.",
    )
    fill_gap = RadioField(
        "Fill the gap?",
        widget=GovRadioInput(),
        choices=[("yes", "Yes"), ("no", "No")],
        validators=[Optional()],
        description=("There is an existing gap with the same team, employment type and role."),
    )
    leave_gap = RadioField(
        "Leave a gap in their previous team?",
        widget=GovRadioInput(),
        choices=[("yes", "Yes"), ("no", "No")],
        validators=[Optional()],
        description="This is only mandatory if moving from one team to another.",
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())


class GapForm(FlaskForm):
    """Record or edit a gap's employment type, role and optional team."""

    employment = SelectField(
        "Employment type",
        widget=GovSelect(),
        choices=[("employee", "Employee"), ("contractor", "Contractor")],
        validators=[InputRequired(message="Select an employment type")],
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
        description="This field is optional.",
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())


class DeleteGapForm(FlaskForm):
    """Confirm permanent removal of a gap."""

    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to remove this gap")],
    )
    submit: SubmitField = SubmitField("Remove gap", widget=GovSubmitInput())


class PersonSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("location", "Location"),
            ("employment", "Employment type"),
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
    employment = RadioField(
        "Employment type",
        widget=GovRadioInput(),
        choices=[
            ("all", "All"),
            ("employee", "Employee"),
            ("contractor", "Contractor"),
        ],
        default="all",
    )
    kind = RadioField(
        "Type",
        widget=GovRadioInput(),
        choices=[
            ("all", "All"),
            ("people", "People"),
            ("gaps", "Gaps"),
        ],
        default="all",
    )
    profession = RadioField(
        "Profession",
        widget=GovRadioInput(),
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
