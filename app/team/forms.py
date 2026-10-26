from typing import Any

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
from wtforms.validators import InputRequired, ValidationError

from app.models import Team


class TeamForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
        description="The team name must be unique.",
    )
    type = SelectField(
        "Type",
        choices=[("", "Select a team type")],
        widget=GovSelect(),
        validators=[InputRequired(message="Select a team type")],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def __init__(self, *args: Any, team: Team | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.team = team
        configured_types = current_app.config.get("TEAM_TYPES", [])
        choices = [("", "Select a team type")]
        choices.extend((team_type, team_type) for team_type in configured_types)
        if team and team.type and team.type not in configured_types:
            choices.append((team.type, team.type))
        self.type.choices = choices

    def validate_name(self, field):
        existing_team = Team.query.filter_by(name=field.data).first()

        if existing_team and (self.team is None or existing_team.id != self.team.id):
            raise ValidationError("A team with this name already exists.")


class TeamSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("type", "Type"),
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
    type = SelectField(
        "Type",
        choices=[("", "Any")],
        widget=GovSelect(),
        default="",
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        configured_types = current_app.config.get("TEAM_TYPES", [])
        self.type.choices = [("", "Any")] + [(team_type, team_type) for team_type in configured_types]


class ArchiveTeamForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this team")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())


class RestoreTeamForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to restore this team")],
    )
    submit: SubmitField = SubmitField("Restore", widget=GovSubmitInput())
